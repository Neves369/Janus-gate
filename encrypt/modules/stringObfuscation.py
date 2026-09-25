import itertools

# -----------------------------------------------------------------------------
# stringObfuscation.py — ofuscação de strings com XOR
# -----------------------------------------------------------------------------
# O XOR é simétrico: (x ^ k) ^ k == x. A MESMA função aplica encriptação e
# decriptação — basta usar a mesma chave nos dois lados.
# O payload saí em bytes arbitrários, por isso o transporte é em hex:
#   - encrypt_string: texto -> bytes UTF-8 -> XOR -> hex (seguro p/ copiar/colar)
#   - decrypt_string: hex -> bytes -> XOR -> texto UTF-8 (volta ao original)
# Falhas possíveis:
#   - hex inválido          -> ValueError          (bytes.fromhex)
#   - chave errada/bytecode -> UnicodeDecodeError  (decode('utf-8'))


def xor_codec(data, key):
    # core: XOR byte a byte (entrada e chave em bytes)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_string(text, key):
    # texto -> bytes UTF-8 -> XOR -> representação textual em hex
    return xor_codec(text.encode('utf-8'), key.encode('utf-8')).hex()


def decrypt_string(cipher_hex, key):
    # hex -> bytes (fromhex) -> XOR -> texto UTF-8 (desfaz a encriptação)
    return xor_codec(bytes.fromhex(cipher_hex), key.encode('utf-8')).decode('utf-8')