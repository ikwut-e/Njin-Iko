import json
import sys
import unicodedata
import openpyxl

# Obolo alphabetical order (digraphs are single sort units)
ALPHABET = ['a', 'b', 'ch', 'd', 'e', 'f', 'g', 'gb', 'h', 'gw', 'i', 'j', 'k', 'kp',
            'kw', 'l', 'm', 'n', 'n̄', 'nw', 'ny', 'o', 'ọ', 'p', 'r', 's', 't',
            'u', 'w', 'y']
ALPHABET_RANK = {letter: i for i, letter in enumerate(ALPHABET)}
MULTI_UNITS = sorted([u for u in ALPHABET if len(u) > 1], key=len, reverse=True)

TONE_MARKS = {'́': 0, '̀': 1, '̂': 2, '̌': 3}  # acute,grave,circumflex,caron
VOWELS = set('aeiou')


def tokenize_alphabet(s):
    """Greedy-tokenize a string into Obolo alphabet units for sorting.
    Spaces/hyphens/apostrophes are ignored (skipped) rather than sorted."""
    s = s.lower()
    tokens = []
    i, n = 0, len(s)
    while i < n:
        if s[i] in (' ', '-', "'"):
            i += 1
            continue
        matched = next((u for u in MULTI_UNITS if s[i:i + len(u)] == u), None)
        if matched:
            tokens.append(matched)
            i += len(matched)
        else:
            tokens.append(s[i])
            i += 1
    return tokens


def orthography_sort_key(orthography):
    if not orthography:
        return ()
    return tuple(ALPHABET_RANK.get(t, 99) for t in tokenize_alphabet(orthography))


def tone_sort_key(toned_orthography):
    """Tone rank per tone-bearing nucleus (vowel or syllabic consonant), in
    order: high/unmarked=0, low=1, falling=2, rising=3. Used only as a
    tie-break when two words are identical under orthography_sort_key."""
    if not toned_orthography:
        return ()
    s = unicodedata.normalize('NFD', toned_orthography.lower())
    tones = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in VOWELS or (c.isalpha() and c not in 'aeiou'):
            is_nucleus = c in VOWELS
            j = i + 1
            found_tone = None
            while j < n and unicodedata.category(s[j]) == 'Mn':
                if s[j] in TONE_MARKS:
                    found_tone = TONE_MARKS[s[j]]
                    is_nucleus = True  # a consonant with a tone mark is syllabic
                j += 1
            if is_nucleus:
                tones.append(found_tone if found_tone is not None else 0)
            i = j
        else:
            i += 1
    return tuple(tones)


def leaf_data(row):
    data = {}
    for key, header in (("ipa", "IPA"), ("orthography", "ORTHOGRAPHY"),
                         ("orthography_toned", "ORTHOGRAPHY (TONED)"),
                         ("pos", "POS"), ("eng", "ENG"), ("fra", "FRA"), ("cf", "CF"),
                         ("var", "VAR"), ("other", "OTHER"), ("notes", "NOTES")):
        val = row.get(header)
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
        word = {"ipa": row.get("IPA"), "senses": []}
        if row.get("ORTHOGRAPHY"):
            word["orthography"] = row.get("ORTHOGRAPHY")
        if row.get("ORTHOGRAPHY (TONED)"):
            word["orthography_toned"] = row.get("ORTHOGRAPHY (TONED)")
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
        subdef["_word_ref"] = word  # used to strip redundant fields later, if applicable
        sense["subdefinitions"].append(subdef)
        example_target = subdef

    for row in rows:
        rtype = row.get("TYPE")
        index = row.get("INDEX")
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
                ex = {"ipa": row.get("IPA")}
                if row.get("ORTHOGRAPHY"):
                    ex["orthography"] = row.get("ORTHOGRAPHY")
                if row.get("ORTHOGRAPHY (TONED)"):
                    ex["orthography_toned"] = row.get("ORTHOGRAPHY (TONED)")
                if row.get("ENG"):
                    ex["eng"] = row.get("ENG")
                if row.get("FRA"):
                    ex["fra"] = row.get("FRA")
                if row.get("NOTES"):
                    ex["notes"] = row.get("NOTES")
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
    headers = [c.value for c in ws[1]]
    raw_rows = list(ws.iter_rows(min_row=2, values_only=True))
    rows = [dict(zip(headers, r)) for r in raw_rows if any(v is not None for v in r)]

    words, warnings = convert(rows)

    has_orthography = any(w.get("orthography") for w in words)
    exceptions = []
    for w in words:
        headword = w.get("orthography") or w.get("ipa")
        for s in w["senses"]:
            for subdef in s["subdefinitions"]:
                word_ref = subdef.pop("_word_ref")
                # a subdef's own ipa/orthography is often identical to the
                # word's headword (most directly when it's literally the same
                # source row that opened the word) - drop each field
                # independently when it matches, rather than repeating it for
                # every entry. Applies to both datasets: when a field
                # genuinely differs (e.g. a subdef with its own distinct
                # phrase), it's kept and flagged below for review.
                for key in ("ipa", "orthography", "orthography_toned"):
                    sub_val, word_val = subdef.get(key), word_ref.get(key)
                    same = sub_val == word_val or (
                        sub_val is not None and word_val is not None
                        and unicodedata.normalize("NFC", sub_val) == unicodedata.normalize("NFC", word_val)
                    )
                    if same:
                        subdef.pop(key, None)
                    elif key in subdef:
                        exceptions.append(
                            f"{headword}: subdef {key}='{subdef.get(key)}' "
                            f"differs from word {key}='{word_ref.get(key)}'"
                        )

    if exceptions:
        print(f"\n{len(exceptions)} subdef/word field difference(s) kept (not redundant):", file=sys.stderr)
        for e in exceptions:
            print(" -", e, file=sys.stderr)

    if has_orthography:
        keyed = [
            (
                (orthography_sort_key(w.get("orthography")), tone_sort_key(w.get("orthography_toned"))),
                w,
            )
            for w in words
        ]
        keyed.sort(key=lambda pair: pair[0])
        words = [w for _, w in keyed]

    with open(out, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(words)} word entries to {out}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(" -", w, file=sys.stderr)


if __name__ == "__main__":
    main()
