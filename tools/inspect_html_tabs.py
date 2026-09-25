with open('web/sovereign_masterpiece.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    for tab in ['id="view-content"', 'id="view-governance"']:
        if tab in line:
            print(f"{tab} found at line {idx+1}")
            for j in range(max(0, idx), min(len(lines), idx + 25)):
                # print without non-ascii
                safe_line = lines[j].encode('ascii', errors='replace').decode('ascii')
                print(f"  {j+1}: {safe_line.strip()[:100]}")
            print("-" * 50)
