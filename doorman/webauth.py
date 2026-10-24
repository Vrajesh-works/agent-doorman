"""Web Bot Auth: Ed25519 signature verification (pure Python, stdlib only).

The IETF Web Bot Auth draft lets a crawler prove its identity with an
Ed25519 signature instead of relying on IP ranges that rotate. This
module implements the cryptographic core: RFC 8032 Ed25519 verification.
It has no dependencies; the point arithmetic is pure Python.

Scope, stated honestly: this verifies an Ed25519 signature over a
message. Building the full RFC 9421 HTTP Message Signatures base string
(covered components, `@signature-params`) is the calling application's
job; ``verify_bot_auth`` below verifies a signature carried in a
``Signature`` header against a message the application constructed.
"""

from __future__ import annotations

import base64
import hashlib

_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _xrecover(y: int) -> int:
    """Recover the x coordinate for a given y on the Edwards curve."""
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q) % _Q
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_BY = (4 * pow(5, _Q - 2, _Q)) % _Q
_BX = _xrecover(_BY)
_BASE_POINT = (_BX, _BY)
_IDENTITY = (0, 1)


def _edwards_add(point_p: tuple[int, int], point_q: tuple[int, int]) -> tuple[int, int]:
    """Add two points on the twisted Edwards curve."""
    x1, y1 = point_p
    x2, y2 = point_q
    denom_x = pow(1 + _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    denom_y = pow(1 - _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    x3 = (x1 * y2 + x2 * y1) * denom_x % _Q
    # Note: a = -1 for Ed25519, so y3 uses + x1*x2 (y1*y2 - a*x1*x2).
    y3 = (y1 * y2 + x1 * x2) * denom_y % _Q
    return (x3, y3)


def _scalarmult(point: tuple[int, int], scalar: int) -> tuple[int, int]:
    """Multiply a point by a scalar (double-and-add)."""
    result = _IDENTITY
    addend = point
    while scalar > 0:
        if scalar & 1:
            result = _edwards_add(result, addend)
        addend = _edwards_add(addend, addend)
        scalar >>= 1
    return result


def _decode_point(data: bytes) -> tuple[int, int]:
    """Decode a 32-byte compressed Edwards point."""
    y = int.from_bytes(data, "little") & ((1 << 255) - 1)
    sign = (data[31] >> 7) & 1
    x = _xrecover(y)
    if (x & 1) != sign:
        x = _Q - x
    return (x, y)


def verify_ed25519(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an RFC 8032 Ed25519 signature.

    Returns True only when the signature is valid for this public key
    and message. Any malformed input returns False, never an exception.
    """
    if len(public_key) != 32 or len(signature) != 64:
        return False
    r_bytes, s_bytes = signature[:32], signature[32:]
    s_value = int.from_bytes(s_bytes, "little")
    if s_value >= _L:
        return False
    try:
        point_a = _decode_point(public_key)
        point_r = _decode_point(r_bytes)
    except (ValueError, IndexError):
        return False
    h_value = int.from_bytes(_sha512(r_bytes + public_key + message), "little")
    left = _scalarmult(_BASE_POINT, s_value)
    right = _edwards_add(point_r, _scalarmult(point_a, h_value))
    return left == right


def verify_bot_auth(
    headers: dict[str, str],
    message: bytes,
    resolve_key: callable,
) -> tuple[bool, str]:
    """Verify a Web Bot Auth style signature from HTTP headers.

    Expects a ``Signature`` header holding a base64 signature (optionally
    in ``sig1=:base64:`` form) and a ``Signature-Agent`` header holding
    a key id the caller's ``resolve_key`` maps to 32 raw public key
    bytes. The caller supplies ``message``, the exact bytes the agent
    signed (per the application's RFC 9421 base-string construction).

    Returns (verified, reason).
    """
    signature_header = headers.get("signature") or headers.get("Signature") or ""
    agent_header = headers.get("signature-agent") or headers.get("Signature-Agent") or ""
    if not signature_header or not agent_header:
        return False, "Missing Signature or Signature-Agent header"
    token = signature_header.strip()
    if token.startswith("sig1="):
        token = token[len("sig1="):].strip()
    token = token.strip(":")
    try:
        signature = base64.b64decode(token, validate=True)
    except (ValueError, base64.binascii.Error):
        return False, "Signature header is not valid base64"
    key_id = agent_header.strip().strip('"')
    public_key = resolve_key(key_id)
    if public_key is None or len(public_key) != 32:
        return False, f"Unknown or invalid key id: {key_id!r}"
    if verify_ed25519(public_key, message, signature):
        return True, f"Signature valid for key {key_id!r}"
    return False, "Signature verification failed"
