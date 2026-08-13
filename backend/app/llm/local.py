"""ตัวสกัดด้วย LLM ที่รันบนเครื่องตัวเอง — ไม่ต้องมี API key ไม่ส่งข้อมูลออกนอกเครื่อง

    LLM_PROVIDER=local
    LOCAL_LLM_BASE_URL=http://localhost:11434/v1     # Ollama (ค่าเริ่มต้น)
    LOCAL_LLM_MODEL=gemma4:26b        # ค่าเริ่มต้น — เหตุผลใน DECISIONS D13

คุยผ่าน **OpenAI-compatible chat completions** ซึ่งเป็นรูปแบบที่ตัวรันในเครื่องแทบทุกตัวรองรับ:

    Ollama       http://localhost:11434/v1    ต้อง  ollama serve
    LM Studio    http://localhost:1234/v1     เปิด Local Server ในแอป
    llama.cpp    http://localhost:8080/v1     llama-server --port 8080
    vLLM         http://localhost:8000/v1

🔒 ผ่าน parse_payload() ตัวเดียวกับ Anthropic — span guard เหมือนกันทุกประการ
   ตัวเล็กที่รันในเครื่องมีโอกาสแต่งข้อความสูงกว่ามาก guard จึงสำคัญกว่าเดิม
   ไม่ใช่ผ่อนลง

🔴 ข้อควรรู้ก่อนคาดหวัง — ตัวเล็กพลาดคนละแบบกับตัวใหญ่
   · **ทำตามคำสั่ง "คัดลอกตรงตัว" ไม่ค่อยได้** — มันชอบเรียบเรียงใหม่ แล้วโดน guard ตัดทิ้ง
     อาการที่จะเห็นคือ "เรียกได้ แต่สกัดได้น้อยกว่า keyword" ซึ่งไม่ใช่ระบบพัง
   · **context สั้น** — รายการทักษะ 73 ตัว + CV ยาว ๆ อาจเกินหน้าต่างของตัว 7B
     ถ้าเจอ ให้ลดขนาดเอกสารหรือใช้ตัวที่ context ยาวกว่า
   · **ตอบไม่เป็น JSON** เป็นเรื่องปกติของตัวเล็ก — เราขอ JSON mode ถ้าเซิร์ฟเวอร์รองรับ
     แต่ไม่พึ่งมัน เพราะบางตัวไม่รองรับแล้วจะ error ทั้งคำขอ

⚠️ ไม่รองรับ HTTPS ที่ต้องยืนยันตัวตน — ตัวนี้ตั้งใจให้ใช้กับเซิร์ฟเวอร์ในเครื่อง
   ถ้าจะชี้ไปหาเซิร์ฟเวอร์ข้างนอก ให้ใช้ provider ที่ทำมาเพื่อการนั้นแทน
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.llm.base import (
    SYSTEM_PROMPT,
    ExtractedSpan,
    ExtractorError,
    parse_payload,
)
from app.seed.skills import SKILLS

# ตัวเล็กบางตัวช้ามากกับ prompt ยาว — เผื่อไว้ให้เครื่องที่ไม่มี GPU
TIMEOUT_SECONDS = 600.0

# 🔴 สูงกว่าฝั่ง Anthropic มาก เพราะ reasoning model (gemma4 · qwen3) เขียนส่วนคิด
#    ยาวหลายพันตัวอักษรก่อนตอบ และโควตานี้แชร์กันระหว่างส่วนคิดกับคำตอบ
#    ตั้งต่ำแล้วจะได้ content ว่างโดยไม่มี error อะไรบอก
MAX_TOKENS = 16000


class LocalExtractor:
    name = "local"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self.base_url = settings.local_llm_base_url.rstrip("/")
        self.model = settings.local_llm_model

    def _skill_catalogue(self) -> str:
        return "\n".join(f'{s["id"]} = {s["name_th"]}' for s in SKILLS)

    def _post(self, body: dict) -> dict:
        client = self._client or httpx.Client(timeout=TIMEOUT_SECONDS)
        try:
            r = client.post(f"{self.base_url}/chat/completions", json=body)
        except httpx.RequestError as exc:
            if isinstance(exc, httpx.TimeoutException):
                raise ExtractorError(
                    f"LLM ในเครื่องตอบไม่ทันใน {TIMEOUT_SECONDS:.0f} วินาที "
                    f"(รุ่น {self.model!r}) — ลองรุ่นเล็กลง หรือลดขนาดเอกสาร"
                ) from exc
            raise ExtractorError(
                f"ต่อกับ LLM ในเครื่องไม่ได้ที่ {self.base_url} — "
                "เปิดเซิร์ฟเวอร์แล้วหรือยัง (ollama serve / LM Studio → Local Server)"
            ) from exc
        finally:
            if self._client is None:
                client.close()

        if r.status_code == 404:
            raise ExtractorError(
                f"เซิร์ฟเวอร์ตอบ 404 ที่ {self.base_url}/chat/completions — "
                "ตรวจว่า LOCAL_LLM_BASE_URL ลงท้ายด้วย /v1 หรือยัง"
            )
        if r.status_code >= 400:
            raise ExtractorError(
                f"เซิร์ฟเวอร์ตอบ {r.status_code}: {r.text[:200]} "
                f"(รุ่นที่ขอคือ {self.model!r} — โหลดรุ่นนี้ไว้แล้วหรือยัง)"
            )
        try:
            return r.json()
        except ValueError as exc:
            raise ExtractorError("เซิร์ฟเวอร์ตอบกลับมาไม่ใช่ JSON") from exc

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        body = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "temperature": 0,          # ต้องได้ผลเดิมทุกครั้ง จะได้วัด before/after ได้
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"รายการทักษะที่รู้จัก:\n{self._skill_catalogue()}\n\n"
                    f"เอกสารของผู้ใช้:\n<document>\n{raw_text}\n</document>"
                )},
            ],
        }
        if settings.local_llm_json_mode:
            # เซิร์ฟเวอร์บางตัวไม่รองรับแล้วจะปฏิเสธทั้งคำขอ จึงปิดได้ด้วย env
            body["response_format"] = {"type": "json_object"}

        payload = self._post(body)
        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ExtractorError(
                f"คำตอบไม่ใช่รูปแบบ OpenAI-compatible: {str(payload)[:200]}"
            ) from exc
        if not isinstance(text, str) or not text.strip():
            # reasoning model ที่คิดยาวจนหมดโควตา จะได้ content ว่างแบบนี้
            thought = (payload.get("choices") or [{}])[0].get("message", {}).get("reasoning")
            hint = (
                f" — รุ่นนี้เขียนส่วนคิดไว้ {len(thought)} ตัวอักษรแล้วไม่เหลือโควตาให้คำตอบ "
                f"ลองเพิ่ม MAX_TOKENS (ตอนนี้ {MAX_TOKENS}) หรือใช้รุ่นที่ไม่ใช่ reasoning"
                if thought else ""
            )
            raise ExtractorError(f"LLM ในเครื่องตอบกลับมาโดยไม่มีข้อความ{hint}")

        return parse_payload(text, raw_text, {s["id"] for s in SKILLS})
