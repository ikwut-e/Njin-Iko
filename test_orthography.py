from build_orthography import process_row

# Precise assertions on isolated, hand-verifiable cases.
cases = [
    ("ácà", 18, "derived", "year",
     "át͡ʃà", "acha", "c -> t͡ʃ (IPA) / ch (ortho), tone stripped in ortho (no hyphen)"),

    ("ò-ráràkà", 18, "derived", "last year",
     "ò-ráràkà", "òraraka", "verb-prefix chunk keeps its (non-acute) tone; root chunk tone-stripped; fused (no hyphen)"),

    ("àk͡pàt-úkót", 89, "derived", "foot print",
     "àk͡pàt-úkót", "akpat-ukot", "compound (2-nuclei first chunk) - hyphen KEPT, tone stripped throughout"),

    ("ɟùgù-ɟúgú", 2403, "word", "chaotic, confused",
     "d͡ʒùgù-d͡ʒúgú", "jugu-jugu", "compound - hyphen kept (2 nuclei first chunk)"),

    ("gwúŋ", 3, "example", "the boy struggled...",
     "gʷúŋ", "Gwun̄.", "gw -> gʷ in IPA (lowercase); ortho keeps gw, word-final ŋ -> n̄, capitalized + period added (eng ends '...')"),

    ("ŋ̀kèt", 9999, "word", "some word",
     "ŋ̀kèt", "nket", "word-initial syllabic ŋ before consonant -> plain n in ortho, unchanged in IPA"),

    ("o ' wa", 9998, "example", "Some sentence.",
     "oꜝwa", "Owa.", "downstep -> symbol in IPA, fully deleted+fused in ortho; period added to match eng"),

    ("íbòt ŋá gê k͡pɔ́j ó-kwéːk m'úwù", 1133, "derived", "some gloss",
     "íbòt ŋá gê k͡pɔ́j ó-kʷéːk múwù", "ibot n̄a ge kpọi okweek m'uwu",
     "kw->kʷ inside hyphenated forms too; ŋá (ŋ-before-VOWEL) -> n̄; o- prefix tone is acute so invisible; bare apostrophe kept; "
     "k͡pɔ́j is word-final j (vowel-preceded) -> i, not y"),

    ("áɲǎ:ɲà", 134, "word", "garden egg, eggplant",
     "áɲǎːɲà", "anyaanya",
     "ASCII ':' -> ː in both columns; ɲ -> ny (unaffected by the new Cj->Ci rule, it's a different source symbol)"),

    # --- new rules requested this round ---

    ("mó wá", 8001, "example", "He is going.",
     None, "Mo wa.", "rule 2: period added to match English, since none was in the source IPA"),

    ("ò kà", 8002, "example", "Is he there?",
     None, "O ka?", "rule 2: question mark added to match English"),

    ("kè", 8003, "word", "a particle",
     "kè", "kè", "rule 3: standalone low-tone 'kè' keeps its grave mark"),

    ("mè", 8004, "word", "a particle",
     "mè", "mè", "rule 3: standalone low-tone 'mè' keeps its grave mark"),

    ("mé", 8005, "word", "a particle (high tone)", None, "me",
     "rule 3 scope check: HIGH tone 'mé' is unaffected (acute is always unmarked anyway)"),

    ("kèjí", 8006, "word", "this/that", None, "keyi",
     "rule 3 scope check: a LONGER word merely starting with kè- must NOT trigger the exception"),

    ("bjà", 287, "word", "remain behind",
     "bjà", "bia", "rule 4: consonant+j cluster -> Ci (by -> bi), tone stripped (no hyphen)"),

    ("jɔ́t", 2364, "word", "difficult, complicated",
     "jɔ́t", "yọt", "rule 4 scope check: word-initial j with NO preceding consonant still maps to y"),

    ("ɟáj", 2366, "word", "some gloss",
     "d͡ʒáj", "jai", "rule 5: word-final j (vowel-preceded) -> i, not y"),

    ("dàwǎj", 398, "word", "some gloss",
     "dàwǎj", "dawai", "rule 5: word-final j after a CARON-toned vowel -> i (tone still stripped, no hyphen)"),

    ("cêj", 340, "word", "some gloss",
     "t͡ʃêj", "chei", "rule 5: word-final j after CIRCUMFLEX-toned vowel -> i"),

    ("k͡pɔ́j gwɔ́ŋ", 8007, "example", "Some phrase.",
     None, "Kpọi gwọn̄.", "rule 5 scope check: j is word-final for its OWN word even mid-sentence, "
     "y-rule still applies to a DIFFERENT word's non-final j (n/a here, no j in 2nd word, just checking no crash)"),

    ("áfránám", 38, "word", "origin",
     "áfáránám", "afaranam", "rule 6 (syncope repair): copy the vowel AFTER r/l (not before), matching user's own example exactly"),

    ("srà", 1947, "word", "gloss",
     "srà", "sra", "rule 6 exception: word-INITIAL clusters (nothing at all before them) are left as-is, no vowel inserted"),

    ("k͡prók", 1134, "word", "gloss",
     "k͡prók", "kprok", "rule 6 exception: word-initial, unchanged"),

    ("mrék", 1303, "word", "gloss",
     "mrék", "mrek", "rule 6 exception: word-initial, unchanged"),

    ("m̀bràbàtì", 1215, "word", "gloss",
     "m̀bàràbàtì", "mbarabati", "rule 6 scope check: preceded by a syllabic nasal (m̀), NOT word-initial -> still gets the epenthetic vowel"),
]

failures = 0
for raw, idx, typ, eng, exp_clean, exp_ortho, note in cases:
    cleaned, ortho = process_row(raw, idx, typ, eng)
    print(f"[{idx}] {raw!r}")
    print(f"   cleaned = {cleaned!r}" + (f"  (expected {exp_clean!r})" if exp_clean else ""))
    print(f"   ortho   = {ortho!r}" + (f"  (expected {exp_ortho!r})" if exp_ortho else ""))
    print(f"   note: {note}")
    if exp_clean is not None and cleaned != exp_clean:
        print("   !! CLEANED MISMATCH")
        failures += 1
    if exp_ortho is not None and ortho != exp_ortho:
        print("   !! ORTHO MISMATCH")
        failures += 1
    print()

print(f"{failures} failure(s) out of {len(cases)} cases")

# Complex real sentences: print-only sanity check (hand-tracing 15+ token
# sentences is error-prone; the full-dataset sweep + isolated rules above
# are what actually verify correctness).
print("\n--- complex real-sentence spot checks (manual eyeball only) ---")
spot = [
    ("mó ' ní-sí í-bèmé òfjɔ́ːŋ-èbékê mèlék icefish, èjí é-kí-dùk jà mìkí-táká", 272, "example",
     "Then he will go and carry a bunch of banana and some dried icefish to eat."),
    ("m̀bérè ótú ínórjè kèjí ó-kàːŋ-bé, énê k͡pé-cîːŋ ìnɔ́ ?", 374, "example",
     "With the way you eat, won't one steal?"),
]
for raw, idx, typ, eng in spot:
    cleaned, ortho = process_row(raw, idx, typ, eng)
    print(f"[{idx}] {raw!r}")
    print(f"   cleaned = {cleaned!r}")
    print(f"   ortho   = {ortho!r}")
    print(f"   eng     = {eng!r}")
    print()
