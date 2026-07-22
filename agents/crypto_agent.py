import os, sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    a = BaseAgent(workspace)

    # 测一下 LLM 在不在
    llm_test = a._llm("ok", timeout=2)
    mode = "AI" if llm_test else "fallback"
    print(f"CryptoAgent @ {workspace} [{mode}]")

    raw = a.read_chal()
    if not raw:
        print("空题？challenge.txt 没内容")
        sys.exit(1)

    print(f"题目 {len(raw)} bytes:")
    print(raw[:200])
    print()

    # 查知识库——以前遇到过类似的吗？
    hits = a.kb_lookup()
    if hits:
        print(f"知识库命中 {len(hits)} 条，优先试已知方法链...")
        for h in hits:
            chain = h.get("chain", [])
            if chain:
                print(f"  #{h['id']}: {chain} (相似度 {h.get('score','?')})")
                # 直接按知识库记录的链依次解码
                cur = raw
                for step in chain:
                    method = step.replace("decode_", "")
                    r = a.decode(cur, method)
                    if r:
                        print(f"    {method} → {r[:80]}...")
                        f = a.grep_flag(r)
                        if f:
                            print(f"FLAG: {f} (via 知识库)")
                            return
                        cur = r
                    else:
                        break

    flag = a.grep_flag(raw)
    if flag:
        print(f"白给！flag 直接在题面里")
        print(f"FLAG: {flag}")
        return

    cur = raw
    tried = set()
    limit = 5

    for rd in range(limit):
        print(f"--- 第 {rd+1} 轮 ---")
        preview = cur[:80].replace("\n", "\\n")
        print(f"[{len(cur)}B] {preview}...")

        # AI 推理编码类型（不通则 fallback）
        candidates = a.ai_sniff(cur)
        todo = []
        for method, conf in candidates:
            key = (method, len(cur))
            if key not in tried:
                todo.append((method, conf))

        # 按置信度排序
        todo.sort(key=lambda x: -x[1])

        if not todo:
            print("没检测出编码，硬试 base64...")
            todo = [("base64", 0.3)]

        hit = False
        for method, conf in todo:
            tried.add((method, len(cur)))
            r = a.decode(cur, method)
            if r is None:
                continue

            conf_tag = "AI" if llm_test else "rx"
            snippet = r[:80].replace("\n", "\\n")
            print(f"  {method} [{conf_tag} conf={conf:.1f}] → {snippet}...")

            f = a.grep_flag(r)
            if f:
                print(f"拿到 flag！链: {method}")
                print(f"FLAG: {f}")
                return

            if a.sniff(r):
                print(f"  还有料，继续扒...")
                cur = r; hit = True; break

            cur = r; hit = True; break

        if not hit:
            print("全试了一遍，跑路")
            break

    f = a.grep_flag(cur)
    if f:
        print(f"最后捞出: {f}")
        print(f"FLAG: {f}")
    else:
        print("没搞出来")
        print(cur[:500])


if __name__ == "__main__":
    main()
