"""Read-only, redacted view of a specified local Antigravity conversation.

Generic protobuf string extraction; this is context recovery, not a claim that
every tool payload is a chat message. Never changes the source database.
"""
import argparse
import re
import sqlite3
import unicodedata
from pathlib import Path


def redact(text):
    text = re.sub(r'(?i)\b(?:sk-|gsk_|AIza)[A-Za-z0-9_\-]{15,}', '[REDACTED KEY]', text)
    text = re.sub(r'(?im)^.*(?:password|api.key|secret|credentials|authorization|bearer|private.key|access.token).*$','[REDACTED SENSITIVE LINE]', text)
    text = re.sub(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', '[EMAIL]', text, flags=re.I)
    text = re.sub(r'\+?\b\d{10,15}\b', '[IDENTIFIER]', text)
    return text


def varint(data, pos):
    value = shift = 0
    while pos < len(data) and shift < 70:
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
        shift += 7
    raise ValueError('invalid varint')


def strings(data, depth=0):
    if depth > 12:
        return []
    result, pos = [], 0
    try:
        while pos < len(data):
            tag, pos = varint(data, pos)
            if tag >> 3 == 0:
                raise ValueError('invalid field')
            wire = tag & 7
            if wire == 0:
                _, pos = varint(data, pos)
            elif wire in (1, 5):
                pos += 8 if wire == 1 else 4
            elif wire == 2:
                length, pos = varint(data, pos)
                if pos + length > len(data):
                    raise ValueError('invalid length')
                raw = data[pos:pos + length]
                pos += length
                nested = strings(raw, depth + 1)
                if nested:
                    result.extend(nested)
                else:
                    try:
                        value = raw.decode('utf-8')
                        if len(value) > 16 and all(c.isprintable() or c in '\n\r\t' or unicodedata.category(c) == 'Cf' for c in value):
                            result.append(value)
                    except UnicodeDecodeError:
                        pass
            else:
                raise ValueError('unsupported wire type')
        return result
    except ValueError:
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--last', type=int, default=0)
    parser.add_argument('--limit', type=int, default=900)
    args = parser.parse_args()
    path = Path('C:/Users/user/.gemini/antigravity/conversations/277e0112-0212-49e1-bd62-d18d4f5929c0.db')
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        rows = db.execute('SELECT idx, step_payload FROM steps WHERE step_type=14 ORDER BY idx').fetchall()
    print('User-type steps:', len(rows))
    if args.last:
        rows = rows[-args.last:]
    for idx, payload in rows:
        texts = strings(payload)
        value = max(texts, key=len, default='[No text recovered]')
        value = redact(value)
        print('\nSTEP', idx, 'characters', len(value), '\n', value[:args.limit])
        if len(value) > args.limit:
            print('[TRUNCATED FOR CONTEXT INDEX]')


if __name__ == '__main__':
    main()
