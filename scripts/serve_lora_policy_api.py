from __future__ import annotations

import argparse
import json
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any


class LoraPolicyRuntime:
    def __init__(
        self,
        *,
        model_id: str,
        adapter_path: Path,
        served_model_name: str,
        max_new_tokens: int,
        use_4bit: bool,
        bf16: bool,
    ):
        self.model_id = model_id
        self.adapter_path = adapter_path
        self.served_model_name = served_model_name
        self.max_new_tokens = max_new_tokens
        self.use_4bit = use_4bit
        self.bf16 = bf16
        self._lock = Lock()
        self._loaded = False
        self._tokenizer = None
        self._model = None

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return

            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

            tokenizer = AutoTokenizer.from_pretrained(self.adapter_path, trust_remote_code=True)
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token = tokenizer.eos_token

            quantization_config = None
            if self.use_4bit:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16 if self.bf16 else torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )

            base = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.bfloat16 if self.bf16 else "auto",
                quantization_config=quantization_config,
            )
            model = PeftModel.from_pretrained(base, self.adapter_path)
            model.eval()

            self._tokenizer = tokenizer
            self._model = model
            self._loaded = True

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.load()
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list.")

        max_tokens = int(payload.get("max_completion_tokens") or payload.get("max_tokens") or self.max_new_tokens)
        temperature = float(payload.get("temperature", 0))
        do_sample = temperature > 0

        tokenizer = self._tokenizer
        model = self._model
        if tokenizer is None or model is None:
            raise RuntimeError("Model failed to load.")

        import torch

        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        generate_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max_tokens,
            "do_sample": do_sample,
            "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        }
        if do_sample:
            generate_kwargs["temperature"] = max(temperature, 1e-5)

        with self._lock:
            with torch.no_grad():
                generated = model.generate(**generate_kwargs)

        prompt_len = inputs["input_ids"].shape[-1]
        content = tokenizer.decode(generated[0][prompt_len:], skip_special_tokens=True).strip()
        now = int(time.time())
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": now,
            "model": self.served_model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": int(inputs["input_ids"].shape[-1]),
                "completion_tokens": int(generated.shape[-1] - prompt_len),
                "total_tokens": int(generated.shape[-1]),
            },
        }


class LoraPolicyHandler(BaseHTTPRequestHandler):
    runtime: LoraPolicyRuntime

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "ok", "loaded": self.runtime.loaded})
            return
        if self.path == "/v1/models":
            self._send_json(
                {
                    "object": "list",
                    "data": [
                        {
                            "id": self.runtime.served_model_name,
                            "object": "model",
                            "created": int(time.time()),
                            "owned_by": "adaptiveroute-local",
                        }
                    ],
                }
            )
            return
        self._send_json({"error": {"message": "Not found"}}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._send_json({"error": {"message": "Not found"}}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            self._send_json(self.runtime.chat(payload))
        except Exception as exc:
            self._send_json({"error": {"message": str(exc)}}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the AdaptiveRoute LoRA routing policy through an OpenAI-compatible API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--model-id", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--adapter-path", default="outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5")
    parser.add_argument("--served-model-name", default="adaptiveroute-routing-policy")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--load-at-startup", action="store_true")
    args = parser.parse_args()

    runtime = LoraPolicyRuntime(
        model_id=args.model_id,
        adapter_path=Path(args.adapter_path),
        served_model_name=args.served_model_name,
        max_new_tokens=args.max_new_tokens,
        use_4bit=not args.no_4bit,
        bf16=args.bf16,
    )
    if args.load_at_startup:
        runtime.load()

    LoraPolicyHandler.runtime = runtime
    server = ThreadingHTTPServer((args.host, args.port), LoraPolicyHandler)
    print(f"Serving {args.served_model_name} on http://{args.host}:{args.port}/v1", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
