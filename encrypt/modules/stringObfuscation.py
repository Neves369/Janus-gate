import itertools


def xor_codec(data, key):
    # core: XOR byte a byte
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_string(text, key):
    # texto -> hex (encriptar)
    return xor_codec(text.encode('utf-8'), key.encode('utf-8')).hex()


def decrypt_string(cipher_hex, key):
    # hex -> texto (decriptar)
    return xor_codec(bytes.fromhex(cipher_hex), key.encode('utf-8')).decode('utf-8')