"""
Crypto Agent — handles crypto/encoding challenges.
Detects encoding types, chains multiple decodings if needed, extracts flag.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from agents.base_agent import BaseAgent


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    agent = BaseAgent(workspace)

    print(f"=== CryptoAgent 启动 ===")
    print(f"工作目录: {workspace}")

    # Step 1: Read challenge
    text = agent.read_challenge()
    if not text:
        print("错误: challenge.txt 为空")
        sys.exit(1)

    print(f"题目内容 ({len(text)} 字符):")
    print(text[:200])
    print()

    # Step 2: Try to find flag directly (maybe it's plaintext?)
    flag = agent.extract_flag(text)
    if flag:
        print(f"=> 直接在原文中找到 flag！")
        print(f"FLAG: {flag}")
        return

    # Step 3: Detect encoding and try decode chain
    current = text
    tried = set()
    max_rounds = 5

    for round_num in range(max_rounds):
        print(f"--- 第 {round_num + 1} 轮解码 ---")
        print(f"当前文本 ({len(current)} 字符): {current[:100]}...")

        # Detect possible encodings
        candidates = agent.detect_encoding(current)
        # Skip already tried combos
        candidates = [c for c in candidates if (c, len(current)) not in tried]

        if not candidates:
            print("没有检测到已知编码，尝试暴力 base64...")
            candidates = ["base64"]

        solved = False
        for enc in candidates:
            key = (enc, len(current))
            if key in tried:
                continue
            tried.add(key)

            decoded = agent.try_decode(current, enc)
            if decoded is None:
                print(f"  {enc}: 解码失败")
                continue

            print(f"  {enc}: 解码成功 → {decoded[:80]}...")

            # Check if decoded result contains flag
            flag = agent.extract_flag(decoded)
            if flag:
                print(f"=> 找到 flag！编码链: {enc}")
                print(f"FLAG: {flag}")
                return

            # Check if decoded result looks like more encoded data
            next_candidates = agent.detect_encoding(decoded)
            if next_candidates:
                print(f"  检测到下一层编码: {next_candidates}")
                current = decoded
                solved = True
                break

            # Even if no next encoding detected, try one more round
            current = decoded
            solved = True
            break

        if not solved:
            print("本轮所有尝试均失败，停止。")
            break

    # Step 4: Final check — maybe decoded text contains flag but with different pattern
    flag = agent.extract_flag(current)
    if flag:
        print(f"=> 最终发现 flag: {flag}")
        print(f"FLAG: {flag}")
    else:
        print("未能解出 flag，最终解码结果：")
        print(current[:500])


if __name__ == "__main__":
    main()
