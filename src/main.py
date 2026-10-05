import sys


def read_lines(path):
    # Raw bytes, split on b"\n"; a trailing empty piece is dropped. "\r" stays in the line.
    with open(path, "rb") as f:
        data = f.read()
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines


def myers(a, b):
    """Shortest edit script from a to b as a list of tags: 'k' keep, '-' delete, '+' insert.

    Works on any two indexable sequences (lists of lines, or strings of characters).
    """
    n, m = len(a), len(b)

    # Common prefix and suffix are always part of some minimal diff, so cut them off.
    p = 0
    while p < n and p < m and a[p] == b[p]:
        p += 1
    s = 0
    while s < n - p and s < m - p and a[n - 1 - s] == b[m - 1 - s]:
        s += 1

    mid = _myers_core(a[p:n - s], b[p:m - s])
    return ["k"] * p + mid + ["k"] * s


def _myers_core(a, b):
    n, m = len(a), len(b)
    if n == 0:
        return ["+"] * m
    if m == 0:
        return ["-"] * n

    max_d = n + m
    off = max_d + 1
    # V[off + k] = furthest x reached on diagonal k (k = x - y).
    V = [0] * (2 * max_d + 3)
    trace = []  # trace[d] = V slice for k in [-d, d] as it was before round d
    found = -1

    for d in range(max_d + 1):
        trace.append(V[off - d:off + d + 1])
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and V[off + k - 1] < V[off + k + 1]):
                x = V[off + k + 1]  # step down: insertion
            else:
                x = V[off + k - 1] + 1  # step right: deletion
            y = x - k
            while x < n and y < m and a[x] == b[y]:  # follow the snake
                x += 1
                y += 1
            V[off + k] = x
            if x >= n and y >= m:
                found = d
                break
        if found >= 0:
            break

    # Walk back from (n, m) to (0, 0), recording edits in reverse.
    ops = []
    x, y = n, m
    for d in range(found, 0, -1):
        v = trace[d]  # state after round d-1; index of diagonal k is k + d
        k = x - y
        if k == -d or (k != d and v[k - 1 + d] < v[k + 1 + d]):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v[prev_k + d]
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:  # snake
            ops.append("k")
            x -= 1
            y -= 1
        ops.append("+" if x == prev_x else "-")
        x, y = prev_x, prev_y
    ops.extend("k" * x)  # leading snake of round 0
    ops.reverse()
    return ops


def char_ranges(old, new):
    """Changed-character ranges ('3-5,9-12' or '.') for the old and new line."""
    old_text = old.decode("utf-8", "surrogateescape")
    new_text = new.decode("utf-8", "surrogateescape")
    old_pos, new_pos = [], []
    i = j = 0
    for tag in myers(old_text, new_text):
        if tag == "k":
            i += 1
            j += 1
        elif tag == "-":
            old_pos.append(i)
            i += 1
        else:
            new_pos.append(j)
            j += 1
    return _to_ranges(old_pos) + b" | " + _to_ranges(new_pos)


def _to_ranges(positions):
    if not positions:
        return b"."
    parts = []
    start = prev = positions[0]
    for pos in positions[1:]:
        if pos == prev + 1:
            prev = pos
            continue
        parts.append((start, prev + 1))
        start = prev = pos
    parts.append((start, prev + 1))
    return ",".join("%d-%d" % r for r in parts).encode()


def build_output(a, b, highlight):
    out = []
    dels, ins = [], []

    def flush():
        for line in dels:
            out.append(b"-" + line + b"\n")
        for t, line in enumerate(ins):
            out.append(b"+" + line + b"\n")
            if highlight and t < len(dels):
                out.append(b"? " + char_ranges(dels[t], line) + b"\n")
        dels.clear()
        ins.clear()

    i = j = 0
    for tag in myers(a, b):
        if tag == "k":
            flush()
            out.append(b" " + a[i] + b"\n")
            i += 1
            j += 1
        elif tag == "-":
            dels.append(a[i])
            i += 1
        else:
            ins.append(b[j])
            j += 1
    flush()
    return b"".join(out)


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)
        return 2
    command, a_path, b_path = sys.argv[1:]
    try:
        a = read_lines(a_path)
        b = read_lines(b_path)
    except OSError as e:
        print("error: cannot read file: %s" % e, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(build_output(a, b, command == "highlight"))
    sys.stdout.buffer.flush()
    return 0


raise SystemExit(main())
