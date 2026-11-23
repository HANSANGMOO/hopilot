def format_table_to_markdown(table_data: list) -> str:
    if not table_data:
        return ""

    header = [str(cell).strip() if cell is not None else "" for cell in table_data[0]]
    num_cols = len(header)

    lines = ["| " + " | ".join(header) + " |"]
    lines.append("|" + ":---|" * num_cols)

    for row in table_data[1:]:
        cells = [str(cell).strip() if cell is not None else "" for cell in row]
        if len(cells) < num_cols:
            cells.extend([""] * (num_cols - len(cells)))
        elif len(cells) > num_cols:
            cells = cells[:num_cols]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)
