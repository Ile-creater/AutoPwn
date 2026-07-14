import os, sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    a = BaseAgent(workspace)

    print(f"CryptoAgent @ {workspace}")

    raw = a.read_chal()
    if not raw:
        print("空题？challenge.txt 没内容")
        sys.exit(1)

    print(f"拿到题目 {len(raw)} bytes:")
    print(raw[:200])
    print()

    # 直接搜 flag（万一题目就是明文）
    flag = a.grep_flag(raw)
    if flag:
        print(f"白给！flag 直接写在题面里")
        print(f"FLAG: {flag}")
        return

    # 递归解，最多 5 层
    cur = raw
    tried = set()
    limit = 5

    for rd in range(limit):
        print(f"--- 第 {rd+1} 轮 ---")
        # 当前状态的简短预览
        preview = cur[:80].replace("\n", "\\n")
        print(f"[{len(cur)}B] {preview}...")

        todo = [c for c in a.sniff(cur) if (c, len(cur)) not in tried]
        if not todo:
            print("嗅不出编码了，硬试 base64...")
            todo = ["base64"]

        hit = False
        for method in todo:
            tried.add((method, len(cur)))
            r = a.decode(cur, method)
            if r is None:
                print(f"  {method} → 解码失败")
                continue

            snippet = r[:80].replace("\n", "\\n")
            print(f"  {method} → {snippet}...")

            f = a.grep_flag(r)
            if f:
                print(f"拿到 flag！链: {method}")
                print(f"FLAG: {f}")
                return

            # 解码出来的还能继续解吗
            if a.sniff(r):
                print(f"  还有料，继续扒...")
                cur = r
                hit = True
                break

            # 没检测到下一层，但也往下走一步碰碰运气
            cur = r
            hit = True
            break

        if not hit:
            print("全试了一遍都不行，跑路")
            break

    # 最后捞一次
    f = a.grep_flag(cur)
    if f:
        print(f"最后捞出: {f}")
        print(f"FLAG: {f}")
    else:
        print("没搞出来，最终结果：")
        print(cur[:500])


if __name__ == "__main__":
    main()
