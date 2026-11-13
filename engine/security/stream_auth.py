import base64
import hashlib
import json
import time
from typing import Dict, Any

class StreamAuthError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

# RFC 8032 pure-python Ed25519 verification
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493

def _inv(z): return pow(z, q - 2, q)
d = -121665 * _inv(121666) % q
I = pow(2, (q - 1) // 4, q)

def _xrecover(y):
    xx = (y * y - 1) * _inv(d * y * y + 1)
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0: x = (x * I) % q
    if x % 2 != 0: x = q - x
    return x

By = 4 * _inv(5) % q
Bx = _xrecover(By)
B = [Bx, By]

def _edwards_add(P, Q):
    x1, y1 = P[0], P[1]
    x2, y2 = Q[0], Q[1]
    x3 = (x1*y2 + x2*y1) * _inv(1 + d*x1*x2*y1*y2) % q
    y3 = (y1*y2 + x1*x2) * _inv(1 - d*x1*x2*y1*y2) % q
    return [x3, y3]

def _scalarmult(P, e):
    if e == 0: return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards_add(Q, Q)
    if e & 1: Q = _edwards_add(Q, P)
    return Q

def _decodeint(s): return int.from_bytes(s, 'little')
def _decodepoint(s):
    y = _decodeint(s) & ((1 << 255) - 1)
    x = _xrecover(y)
    if bool(x & 1) != bool(s[31] & 0x80): x = q - x
    return [x, y]

def verify_ed25519(public_key_bytes: bytes, message: bytes, signature_bytes: bytes) -> bool:
    try:
        if len(public_key_bytes) != 32 or len(signature_bytes) != 64:
            return False
        R = _decodepoint(signature_bytes[:32])
        A = _decodepoint(public_key_bytes)
        S = _decodeint(signature_bytes[32:])
        h = _decodeint(hashlib.sha512(signature_bytes[:32] + public_key_bytes + message).digest())
        SB = _scalarmult(B, S)
        RA = _edwards_add(R, _scalarmult(A, h))
        return SB[0] == RA[0] and SB[1] == RA[1]
    except Exception:
        return False

def _b64url_decode(s: str) -> bytes:
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)

def verify_stream_token(token: str, camera_id: str, jwks: Dict[str, Any]) -> Dict[str, Any]:
    if len(token) > 4096:
        raise StreamAuthError('TOKEN_TOO_LARGE', 'Token length exceeds maximum limit')

    parts = token.split('.')
    if len(parts) != 3:
        raise StreamAuthError('INVALID_TOKEN_FORMAT', 'Token must contain 3 segments')

    h_b64, p_b64, s_b64 = parts

    try:
        header = json.loads(_b64url_decode(h_b64).decode('utf-8'))
    except Exception:
        raise StreamAuthError('MALFORMED_HEADER', 'Malformed token header')

    if header.get('alg') != 'EdDSA':
        raise StreamAuthError('UNSUPPORTED_ALGORITHM', f"Expected EdDSA, got {header.get('alg')}")

    if header.get('typ') != 'stream+jwt':
        raise StreamAuthError('INVALID_TOKEN_TYPE', f"Expected stream+jwt, got {header.get('typ')}")

    kid = header.get('kid')
    if not kid:
        raise StreamAuthError('MISSING_KEY_ID', 'Header missing kid')

    # Resolve key from JWKS
    keys_list = jwks.get('keys', [])
    matched_jwk = next((k for k in keys_list if k.get('kid') == kid), None)
    if not matched_jwk:
        raise StreamAuthError('UNKNOWN_KEY', f'Unknown key id: {kid}')

    raw_x = matched_jwk.get('x')
    if not raw_x:
        raise StreamAuthError('INVALID_JWK', 'JWK missing x coordinate')

    public_key_bytes = _b64url_decode(raw_x)
    sig_bytes = _b64url_decode(s_b64)
    signing_input = f"{h_b64}.{p_b64}".encode('ascii')

    if not verify_ed25519(public_key_bytes, signing_input, sig_bytes):
        raise StreamAuthError('INVALID_SIGNATURE', 'Cryptographic signature verification failed')

    try:
        payload = json.loads(_b64url_decode(p_b64).decode('utf-8'))
    except Exception:
        raise StreamAuthError('MALFORMED_PAYLOAD', 'Malformed token payload')

    if payload.get('iss') != 'border-ai':
        raise StreamAuthError('INVALID_ISSUER', 'Issuer mismatch')

    if payload.get('aud') != 'border-ai-stream':
        raise StreamAuthError('INVALID_AUDIENCE', 'Audience mismatch')

    now = int(time.time())
    exp = payload.get('exp', 0)
    if exp < now - 5:
        raise StreamAuthError('TOKEN_EXPIRED', 'Stream token has expired')

    if payload.get('cam') != camera_id:
        raise StreamAuthError('CAMERA_MISMATCH', f"Token camera {payload.get('cam')} does not match requested camera {camera_id}")

    return payload
