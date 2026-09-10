import json
import sys
import openpyxl

COL_IPA, COL_TYPE, COL_POS, COL_ENG, COL_FRA, COL_CF, COL_VAR, COL_OTHER, COL_INDEX, COL_NOTES = range(10)


def cell(row, col):
    return row[col] if col < len(row) else None


def leaf_data(row):
    data = {"ipa": cell(row, COL_IPA)}
    for key, col in (("pos", COL_POS), ("eng", COL_ENG), ("fra", COL_FRA),
                      ("cf", COL_CF), ("var", COL_VAR), ("other", COL_OTHER),
                      ("notes", COL_NOTES)):
        val = cell(row, col)
        if val is not None and val != "":
            data[key] = val
    return data


def convert(rows):
    words = []
    word = sense = subdef = None
    example_target = None  # dict that "examples" get appended to (a subdef, derived, or related)
    warnings = []

    def new_word(row):
        nonlocal word, sense, subdef, example_target
        word = {"ipa": cell(row, COL_IPA), "senses": []}
        words.append(word)
        new_sense(row)

    def new_sense(row):
        nonlocal sense, subdef, example_target
        sense = {"subdefinitions": []}
        word["senses"].append(sense)
        new_subdef(row)

    def new_subdef(row):
        nonlocal subdef, example_target
        subdef = leaf_data(row)
        sense["subdefinitions"].append(subdef)
        example_target = subdef

    for row in rows:
        rtype = cell(row, COL_TYPE)
        index = cell(row, COL_INDEX)
        if rtype is None or rtype == "":
            warnings.append(f"row {index}: blank TYPE, treated as 'word'")
            rtype = "word"

        if rtype == "word":
            new_word(row)
        elif rtype == "sense":
            if word is None:
                warnings.append(f"row {index}: 'sense' with no open word, treated as 'word'")
                new_word(row)
            else:
                new_sense(row)
        elif rtype == "subdef":
            if sense is None:
                warnings.append(f"row {index}: 'subdef' with no open sense, treated as 'word'")
                new_word(row)
            else:
                new_subdef(row)
        elif rtype in ("derived", "related"):
            if subdef is None:
                warnings.append(f"row {index}: '{rtype}' with no open subdefinition, treated as 'word'")
                new_word(row)
            else:
                d = leaf_data(row)
                subdef.setdefault(rtype, []).append(d)
                example_target = d
        elif rtype == "example":
            if example_target is None:
                warnings.append(f"row {index}: 'example' with no open subdefinition/derived/related, treated as 'word'")
                new_word(row)
            else:
                ex = {"ipa": cell(row, COL_IPA)}
                if cell(row, COL_ENG):
                    ex["eng"] = cell(row, COL_ENG)
                if cell(row, COL_FRA):
                    ex["fra"] = cell(row, COL_FRA)
                if cell(row, COL_NOTES):
                    ex["notes"] = cell(row, COL_NOTES)
                example_target.setdefault("examples", []).append(ex)
        else:
            warnings.append(f"row {index}: unknown TYPE '{rtype}', treated as 'word'")
            new_word(row)

    return words, warnings


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "obolo_dict.xlsx"
    out = sys.argv[2] if len(sys.argv) > 2 else src.rsplit(".", 1)[0] + ".json"

    wb = openpyxl.load_workbook(src, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    rows = [r for r in rows if any(v is not None for v in r)]

    words, warnings = convert(rows)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(words)} word entries to {out}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(" -", w, file=sys.stderr)


if __name__ == "__main__":
    main()
