"""
Cleans the IPA column and derives an ORTHOGRAPHY column from it.

Both outputs are computed independently from the same original raw IPA
string (not chained from one to the other), since the two target
conventions map overlapping source symbols onto different targets
(e.g. orthography maps both 'ɟ' and 'j' onto distinct outputs - chaining
ɟ->j then j->y would corrupt the ɟ result).
"""
import re
import unicodedata

ACUTE = '́'       # H (high) - always unmarked in orthography
GRAVE = '̀'       # L (low)
CIRCUMFLEX = '̂'  # HL (falling)
CARON = '̌'       # LH (rising)
TONE_MARKS = {ACUTE, GRAVE, CIRCUMFLEX, CARON}
TIE_BAR = '͡'
LONG = 'ː'        # ː
DOWNSTEP_OUT = 'ꜝ'  # ꜝ
VOWELS = set('aeiouɔ')

LOANWORD_TEXT = {272: "icefish"}  # row INDEX -> literal loanword substring
PLACEHOLDER = ''  # private-use char: passes through all rules untouched


def nfd(s):
    return unicodedata.normalize('NFD', s)


def tokenize(raw):
    """NFD-normalize, merge tie-bar digraphs (k͡p, ɡ͡b) into single tokens,
    and fix the ASCII-colon-for-length-mark typo (both derived outputs
    should reflect this correction, not just the cleaned-IPA one)."""
    chars = list(nfd(raw))
    tokens = []
    i = 0
    while i < len(chars):
        if i + 2 < len(chars) and chars[i + 1] == TIE_BAR:
            tokens.append(chars[i] + chars[i + 1] + chars[i + 2])
            i += 3
        elif chars[i] == ':':
            tokens.append(LONG)
            i += 1
        else:
            tokens.append(chars[i])
            i += 1
    return tokens


def is_consonant_token(t):
    return (
        t not in VOWELS
        and t not in TONE_MARKS
        and t not in (LONG, ' ', ',', '?', '-', "'", ':')
    )


def count_nuclei(chunk_tokens):
    n = 0
    for i, t in enumerate(chunk_tokens):
        if t in VOWELS:
            n += 1
        elif is_consonant_token(t):
            if i + 1 < len(chunk_tokens) and chunk_tokens[i + 1] in TONE_MARKS:
                n += 1  # syllabic consonant bearing tone
    return n


def fill_syncope_vowels(tokens):
    """Cluster+r/l onsets (fr, tr, k͡pr, ɡ͡br, ...) are the result of historical
    vowel syncope - restore the deleted vowel by copying the vowel (with its
    tone) that immediately follows the r/l, inserting it before the r/l.
    e.g. afranam -> afaranam (copies the 'a' after 'r', not the one before 'f').
    Word-initial clusters (nothing at all before the first consonant) are left
    alone - e.g. 'srà', 'k͡prók', 'mrék' keep their cluster as-is."""
    out = []
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        out.append(t)
        word_initial = (i == 0 or tokens[i - 1] == ' ')
        if (
            not word_initial
            and is_consonant_token(t) and t not in ('r', 'l', 'w', 'j')
            and i + 1 < n and tokens[i + 1] in ('r', 'l')
        ):
            j = i + 2
            if j < n and tokens[j] in VOWELS:
                out.append(tokens[j])
                if j + 1 < n and tokens[j + 1] in TONE_MARKS:
                    out.append(tokens[j + 1])
        i += 1
    return out


# ---------------------------------------------------------------------------
# Cleaned IPA  (tone marks are left untouched - only phoneme substitutions,
# downstep symbol, and stray punctuation/typo cleanup)
# ---------------------------------------------------------------------------

def clean_ipa_tokens(tokens):
    out = []
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < n else None
        if t in ('k', 'g', 'ŋ') and nxt == 'w':
            out.append(t + 'ʷ')  # ʷ
            i += 2
        elif t == 'ɟ':
            out.append('d' + TIE_BAR + 'ʒ')  # d͡ʒ
            i += 1
        elif t == 'c':
            out.append('t' + TIE_BAR + 'ʃ')  # t͡ʃ
            i += 1
        elif t in (',', '?'):
            i += 1  # drop stray punctuation - IPA column should be pure IPA
        elif t == "'":
            before = tokens[i - 1] if i > 0 else None
            after = tokens[i + 1] if i + 1 < n else None
            if before == ' ' and after == ' ':
                out.pop()  # remove the space already appended for `before`
                out.append(DOWNSTEP_OUT)
                i += 2  # skip apostrophe + the following space
            else:
                i += 1  # bare elision apostrophe: delete outright, join letters
        else:
            out.append(t)
            i += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Orthography
# ---------------------------------------------------------------------------

def remove_downstep_spacing(tokens):
    """For orthography: ' X ' -> X fused with no space at all (o ' wa -> owa)."""
    out = []
    i, n = 0, len(tokens)
    while i < n:
        if (
            tokens[i] == "'"
            and i > 0 and out and out[-1] == ' '
            and i + 1 < n and tokens[i + 1] == ' '
        ):
            out.pop()  # drop the space before
            i += 2     # skip apostrophe + space after
        else:
            out.append(tokens[i])
            i += 1
    return out


def split_words_and_chunks(tokens):
    """tokens (no downstep-spacing) -> list of words, each a list of chunks,
    each chunk a list of tokens (hyphens dropped, spaces are word breaks)."""
    words = []
    cur_word = []
    cur_chunk = []

    def flush_chunk():
        cur_word.append(list(cur_chunk))
        cur_chunk.clear()

    def flush_word():
        flush_chunk()
        words.append(list(cur_word))
        cur_word.clear()

    for t in tokens:
        if t == ' ':
            flush_word()
        elif t == '-':
            flush_chunk()
        else:
            cur_chunk.append(t)
    flush_word()
    return words


def syllabic_ng_word_initial(chunks):
    """True if this word's first token is a syllabic word-initial ŋ
    (own syllable, next real phoneme is a consonant, and it's not ŋw)."""
    if not chunks or not chunks[0] or chunks[0][0] != 'ŋ':
        return False
    first = chunks[0]
    if len(first) > 1 and first[1] == 'w':
        return False  # that's ŋw, handled separately
    j = 1
    while j < len(first) and first[j] in TONE_MARKS:
        j += 1
    if j < len(first):
        return is_consonant_token(first[j])
    # nothing left in this chunk after the tone marks - peek at next chunk
    if len(chunks) > 1 and chunks[1]:
        return is_consonant_token(chunks[1][0])
    return False


def orthography_chunk(chunk_tokens, keep_tone, force_first_ng_as_n, is_last_chunk, keep_acute=False):
    out = []
    i, n = 0, len(chunk_tokens)
    while i < n:
        t = chunk_tokens[i]
        nxt = chunk_tokens[i + 1] if i + 1 < n else None
        prev = chunk_tokens[i - 1] if i > 0 else None

        if t == 'k͡p':
            out.append('kp')
        elif t == 'ɡ͡b':  # ɡ͡b
            out.append('gb')
        elif t == 'ŋ' and nxt == 'w':
            out.append('nw')
            i += 2
            continue
        elif t == 'ɟ':
            out.append('j')
        elif t == 'ɲ':
            out.append('ny')
        elif t == 'ɔ':
            out.append('ọ')
        elif t == 'c':
            out.append('ch')
        elif t == 'j':
            # -> i when preceded by a consonant (Cj cluster, e.g. by/fy/ry
            # -> bi/fi/ri) OR when word-final (approximating syllable-final,
            # which suffices for this data - no cases of j sitting right
            # before a hyphen occur). Otherwise -> y. Never touches ɲ->ny,
            # which comes from a separate source symbol.
            consonant_before = prev is not None and is_consonant_token(prev)
            word_final = is_last_chunk and all(
                chunk_tokens[k] in TONE_MARKS for k in range(i + 1, n)
            )
            out.append('i' if (consonant_before or word_final) else 'y')
        elif t == 'ŋ':
            out.append('n' if (i == 0 and force_first_ng_as_n) else 'n̄')
        elif t == LONG:
            if out and out[-1]:
                base = out[-1][0]
                tone = out[-1][1:] if len(out[-1]) > 1 else ''
                if tone == CIRCUMFLEX:  # HL falling -> H then L across the two moras
                    out[-1] = base + ACUTE
                    out.append(base + GRAVE)
                elif tone == CARON:  # LH rising -> L then H across the two moras
                    out[-1] = base + GRAVE
                    out.append(base + ACUTE)
                elif tone in (ACUTE, GRAVE):  # level tone -> same tone on both moras
                    out.append(base + tone)
                else:
                    out.append(base)  # no tone attached - bare vowel on both
            i += 1
            continue
        elif t in TONE_MARKS:
            if keep_tone and (t != ACUTE or keep_acute) and out:
                out[-1] = out[-1] + t  # attach to the segment it belongs to
            i += 1
            continue
        elif t == "'":
            out.append("'")  # bare elision apostrophe: kept literally
        else:
            out.append(t)
        i += 1
    return ''.join(out)


def is_ke_me_low_tone(chunk):
    """Standalone 'kè' or 'mè' (low tone) - a distinct grammatical particle
    from unmarked 'ke'/'me' (high/unspecified tone), so its tone is kept."""
    return len(chunk) == 3 and chunk[0] in ('k', 'm') and chunk[1] == 'e' and chunk[2] == GRAVE


def build_orthography(tokens, full_tone=False):
    """full_tone=True produces a reference form that keeps every tone mark
    (including acute/high) instead of the normal "acute is unmarked, only
    verb-prefixes keep non-acute tone" display convention. Structural
    choices (hyphen-for-compound vs fused-for-verb, ny/ch/kp/gb etc.) are
    unchanged - only the tone-stripping behavior differs."""
    tokens = remove_downstep_spacing(tokens)
    words = split_words_and_chunks(tokens)
    out_words = []
    for chunks in words:
        force_n = syllabic_ng_word_initial(chunks)
        is_verb_form = len(chunks) > 1 and count_nuclei(chunks[0]) == 1
        rendered = []
        for ci, chunk in enumerate(chunks):
            keep_tone = full_tone or (ci == 0 and is_verb_form) or (
                len(chunks) == 1 and is_ke_me_low_tone(chunk)
            )
            rendered.append(
                orthography_chunk(chunk, keep_tone, force_n and ci == 0,
                                   ci == len(chunks) - 1, keep_acute=full_tone)
            )
        joiner = '' if is_verb_form else '-'
        out_words.append(joiner.join(rendered))
    return ' '.join(out_words)


def capitalize(s, should_cap):
    if should_cap and s:
        return s[0].upper() + s[1:]
    return s


def process_row(raw_ipa, row_index, row_type, eng):
    loanword = LOANWORD_TEXT.get(row_index)
    working = raw_ipa
    if loanword and loanword in working:
        working = working.replace(loanword, PLACEHOLDER)

    tokens = tokenize(working)
    tokens = fill_syncope_vowels(tokens)

    cleaned = clean_ipa_tokens(tokens)
    if loanword:
        cleaned = cleaned.replace(PLACEHOLDER, f'<{loanword}>')
    cleaned = unicodedata.normalize('NFC', cleaned).strip()

    ortho = build_orthography(tokens)
    if loanword:
        ortho = ortho.replace(PLACEHOLDER, loanword)
    should_cap = (row_type == 'example') or bool(eng and eng[0:1].isupper())
    ortho = capitalize(ortho, should_cap)
    if row_type == 'example' and eng:
        eng_stripped = eng.rstrip()
        if eng_stripped and eng_stripped[-1] in '.!?':
            ortho = ortho.rstrip()
            while ortho and ortho[-1] in '.!?,':
                ortho = ortho[:-1].rstrip()
            ortho = ortho + eng_stripped[-1]
    ortho = unicodedata.normalize('NFC', ortho).strip()

    return cleaned, ortho


def reconstruct_pseudo_raw(cleaned_ipa):
    """Reverse the cleaned-IPA substitutions to feed the existing
    raw-IPA-oriented pipeline. Used when the source we have on hand is the
    already-cleaned IPA column (e.g. after manual edits were made directly
    to it, so re-deriving from a stale pristine backup would lose them)."""
    s = cleaned_ipa
    s = s.replace('ŋ' + 'ʷ', 'ŋw')
    s = s.replace('k' + 'ʷ', 'kw')
    s = s.replace('g' + 'ʷ', 'gw')
    s = s.replace('d' + TIE_BAR + 'ʒ', 'ɟ')
    s = s.replace('t' + TIE_BAR + 'ʃ', 'c')
    s = s.replace(DOWNSTEP_OUT, " ' ")
    s = re.sub(r'<([^>]*)>', r'\1', s)
    return s


def toned_orthography(raw_ipa, row_index):
    """Reference form for sorting: orthography with every tone mark kept
    (including acute/high), lowercase, no sentence-style capitalization."""
    loanword = LOANWORD_TEXT.get(row_index)
    working = raw_ipa
    if loanword and loanword in working:
        working = working.replace(loanword, PLACEHOLDER)

    tokens = tokenize(working)
    tokens = fill_syncope_vowels(tokens)

    toned = build_orthography(tokens, full_tone=True)
    if loanword:
        toned = toned.replace(PLACEHOLDER, loanword)
    return unicodedata.normalize('NFC', toned).strip()
