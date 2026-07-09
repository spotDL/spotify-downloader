"""Per-signal pure feature functions, ported verbatim from spotDL v4.

Each function extracts one raw signal from a ``(Track, AudioCandidate)`` pair.
The arithmetic mirrors ``spotdl.utils.matching`` (v4) line-by-line — the
thresholds, fixups, exp-decay duration curve, and the load-bearing
``FORBIDDEN_WORDS`` duplicates are all preserved so the golden-corpus gate can
match v4 behavior. Penalty *magnitudes* and blend thresholds live in
``matching.scoring`` (Task 5), not here; these functions only produce signals.

v4 provenance (function -> v5 function):
    check_common_word        -> common_word_overlap
    calc_name_match          -> title_similarity   (search_query branch dropped)
    calc_main_artist_match   -> main_artist_similarity
    calc_artists_match       -> other_artist_similarity
    order_results (artist pipeline) + artists_match_fixup1/2/3 -> artist_similarity
    calc_album_match         -> album_similarity
    calc_time_match          -> duration_similarity
    check_forbidden_words    -> forbidden_words
    calc_album_match etc.

Two intentional near-parity gaps (documented in the brief):
  * ``explicit_mismatch`` is inert (``AudioCandidate`` has no ``explicit``
    field); it reads ``getattr(candidate, "explicit", None)`` so it activates
    automatically if a later plan adds the field.
  * ``album_similarity`` returns ``None`` (not ``0.0``) when the candidate has
    no album, so scoring can distinguish "no info" from "mismatch".
"""

from itertools import product, zip_longest
from math import exp

from spotdl_core.matching.text import (
    based_sort,
    clean_string,
    fill_string,
    ratio,
    sequence_ratio,
    slugify,
    song_title,
    sort_tokens,
)
from spotdl_core.model import AudioCandidate, FeatureVector, Track

# Verbatim from v4 (spotdl/utils/matching.py). Duplicates are load-bearing:
# v4's check_forbidden_words appends one entry per list *entry* and order_results
# subtracts 15 per entry, so a "remix" hit costs -30 and a "cover" hit -15.
FORBIDDEN_WORDS: tuple[str, ...] = (
    "bassboosted",
    "remix",
    "remastered",
    "remaster",
    "reverb",
    "bassboost",
    "live",
    "acoustic",
    "8daudio",
    "concert",
    "live",
    "acapella",
    "slowed",
    "instrumental",
    "remix",
    "cover",
    "reverb",
)


# --------------------------------------------------------------------------- #
# internal helpers
# --------------------------------------------------------------------------- #
def _ratio_opt(string1: str | None, string2: str | None) -> float:
    """v4-faithful ``ratio`` that tolerates ``None`` (zip_longest fill).

    v4 called ``fuzz.ratio(x, None)`` directly, which rapidfuzz scores as 0.
    Our cached ``ratio`` is str-typed, so mirror that behavior explicitly.
    """
    if string1 is None or string2 is None:
        return 0.0
    return ratio(string1, string2)


def _create_match_strings(track: Track, candidate: AudioCandidate) -> tuple[str, str]:
    """v4 ``create_match_strings`` with the ``search_query`` branch dropped.

    Fills each side with missing artists, then ``based_sort``s and rejoins.
    """
    slug_song_name = slugify(track.name)
    slug_song_title = slugify(song_title(track.name, track.artists))

    test_str1 = slugify(candidate.name)
    test_str2 = slug_song_name if candidate.verified else slug_song_title

    # Fill strings with missing artists (order matters: str1 then str2).
    test_str1 = fill_string(track.artists, test_str1, test_str2)
    test_str2 = fill_string(track.artists, test_str2, test_str1)

    test_list1, test_list2 = based_sort(test_str1.split("-"), test_str2.split("-"))
    return "-".join(test_list1), "-".join(test_list2)


# --------------------------------------------------------------------------- #
# feature functions
# --------------------------------------------------------------------------- #
def common_word_overlap(track: Track, candidate: AudioCandidate) -> bool:
    """v4 ``check_common_word``: any non-empty ``slugify(track.name)`` word is a
    substring of the de-hyphenated ``slugify(candidate.name)``."""
    sentence_words = slugify(track.name).split("-")
    to_check = slugify(candidate.name).replace("-", "")
    return any(word != "" and word in to_check for word in sentence_words)


def title_similarity(track: Track, candidate: AudioCandidate) -> float:
    """v4 ``calc_name_match`` without the ``search_query`` branch (0..100)."""
    match_str1, match_str2 = _create_match_strings(track, candidate)
    result_name, song_name = slugify(candidate.name), slugify(track.name)

    res_list, song_list = based_sort(result_name.split("-"), song_name.split("-"))
    result_name, song_name = "-".join(res_list), "-".join(song_list)

    name_match = ratio(result_name, song_name)
    if name_match <= 75:
        name_match = max(name_match, ratio(match_str1, match_str2))
    return name_match


def main_artist_similarity(track: Track, candidate: AudioCandidate) -> float:
    """v4 ``calc_main_artist_match`` verbatim (0..100)."""
    main_artist_match = 0.0

    if not candidate.artists:
        return main_artist_match

    song_artists = list(map(slugify, track.artists))
    result_artists = list(map(slugify, candidate.artists))
    # v5 based_sort is non-mutating; song_artists/result_artists keep their order.
    _, sorted_result_artists = based_sort(song_artists, result_artists)

    slug_song_main_artist = slugify(track.artists[0])
    slug_result_main_artist = sorted_result_artists[0]

    # Candidate collapsed multiple artists into one string.
    if len(track.artists) > 1 and len(candidate.artists) == 1:
        for artist in map(slugify, track.artists[1:]):
            artist_sorted = sort_tokens(tuple(slugify(artist).split("-")))
            res_main_artist = sort_tokens(tuple(slug_result_main_artist.split("-")))
            if artist_sorted in res_main_artist:
                main_artist_match += 100 / len(track.artists)
        return main_artist_match

    main_artist_match = ratio(slug_song_main_artist, slug_result_main_artist)

    # Fallback: v4 fed the *mutated* (lex-sorted) song_artists and the
    # based_sort()-returned (reverse-lex) result list. Reproduce those exactly:
    # sorted(song_artists) for the track side, sorted_result_artists for cand.
    if main_artist_match < 50 and len(song_artists) > 1:
        for song_artist, result_artist in product(
            sorted(song_artists)[:2], sorted_result_artists[:2]
        ):
            main_artist_match = max(main_artist_match, ratio(song_artist, result_artist))

    return main_artist_match


def other_artist_similarity(track: Track, candidate: AudioCandidate) -> float:
    """v4 ``calc_artists_match`` verbatim (0..100)."""
    if len(track.artists) == 1 or not candidate.artists:
        return 0.0

    artist1_list, artist2_list = based_sort(
        list(map(slugify, track.artists)), list(map(slugify, candidate.artists))
    )

    # Drop the main artist from both.
    artist1_list, artist2_list = artist1_list[1:], artist2_list[1:]

    artists_match = 0.0
    for artist1, artist2 in zip_longest(artist1_list, artist2_list):
        artists_match += _ratio_opt(artist1, artist2)

    return artists_match / len(artist1_list)


def _artists_match_fixup1(track: Track, candidate: AudioCandidate, score: float) -> float:
    """v4 ``artists_match_fixup1`` — non-verified fixups."""
    if candidate.verified or score > 50:
        return score

    # Fall back to channel-name match.
    channel_name_match = ratio(
        slugify(track.main_artist),
        slugify(", ".join(candidate.artists)) if candidate.artists else "",
    )
    score = max(score, channel_name_match)

    # Fall back to matching artist slugs against the candidate title.
    if score <= 70:
        artist_title_match = 0.0
        result_name = slugify(candidate.name).replace("-", "")
        for artist in track.artists:
            slug_artist = slugify(artist).replace("-", "")
            if slug_artist in result_name:
                artist_title_match += 1.0
        artist_title_match = (artist_title_match / len(track.artists)) * 100
        score = max(score, artist_title_match)

    # Fall back to a token-tuple ratio over all artist slug tokens.
    if score <= 70:
        artist_list1: list[str] = []
        for artist in track.artists:
            artist_list1.extend(slugify(artist).split("-"))
        artist_list2: list[str] = []
        for artist in candidate.artists:
            artist_list2.extend(slugify(artist).split("-"))
        score = max(score, sequence_ratio(tuple(artist_list1), tuple(artist_list2)))

    return score


def _artists_match_fixup2(track: Track, candidate: AudioCandidate, score: float) -> float:
    """v4 ``artists_match_fixup2`` — verified fixups."""
    if score > 70 or not candidate.verified:
        return score

    slug_song_name = slugify(track.name)
    slug_result_name = slugify(candidate.name)

    has_main_artist = (score / (2 if len(track.artists) > 1 else 1)) > 50

    _, match_str2 = _create_match_strings(track, candidate)

    artists_to_check = track.artists[int(has_main_artist) :]
    for artist in artists_to_check:
        slug_artist = slugify(artist).replace("-", "")
        if slug_artist in match_str2.replace("-", ""):
            score += 5

    if score <= 70:
        # v4 fell back to result.author when result.artists was falsy; v5 has no
        # channel-author field, so the fallback is ("",).
        artist_list1 = clean_string(track.artists, slug_song_name, sort=True)
        artist_list2 = clean_string(
            candidate.artists if candidate.artists else ("",),
            slug_result_name,
            sort=True,
        )
        score = max(score, ratio(artist_list1, artist_list2))

    return score


def _artists_match_fixup3(track: Track, candidate: AudioCandidate, score: float) -> float:
    """v4 ``artists_match_fixup3`` — single-candidate-artist / multi-track fixup."""
    if score > 70 or len(candidate.artists) != 1 or len(track.artists) == 1:
        return score

    fix = ratio(
        slugify(candidate.name),
        slugify(song_title(track.name, (track.main_artist,))),
    )
    if fix >= 80:
        score = (score + fix) / 2

    return score


def artist_similarity(track: Track, candidate: AudioCandidate) -> float:
    """Composed artist score: v4 ``order_results`` artist pipeline + fixup1/2/3.

    ``(main + other) / (2 if multi-artist else 1)`` then the three fixups with
    their exact internal gates. Clamped to 100.
    """
    score = main_artist_similarity(track, candidate) + other_artist_similarity(track, candidate)
    score = score / (2 if len(track.artists) > 1 else 1)

    score = _artists_match_fixup1(track, candidate, score)
    score = _artists_match_fixup2(track, candidate, score)
    score = _artists_match_fixup3(track, candidate, score)

    return min(score, 100)


def album_similarity(track: Track, candidate: AudioCandidate) -> float | None:
    """v4 ``calc_album_match`` — but ``None`` (not ``0.0``) when candidate has no
    album, so scoring can distinguish "no info" from "mismatch"."""
    if not candidate.album:
        return None
    return ratio(slugify(track.album.name if track.album else ""), slugify(candidate.album))


def duration_delta_s(track: Track, candidate: AudioCandidate) -> float:
    """Absolute duration difference in seconds. Unknown candidate duration -> the
    full track length (drives ``duration_similarity`` toward 0, as v4)."""
    return abs(track.duration_ms - (candidate.duration_ms or 0)) / 1000.0


def duration_similarity(track: Track, candidate: AudioCandidate) -> float:
    """v4 ``calc_time_match``: ``exp(-0.1 * delta_s) * 100`` (0..100)."""
    return exp(-0.1 * duration_delta_s(track, candidate)) * 100


def forbidden_words(track: Track, candidate: AudioCandidate) -> tuple[str, ...]:
    """v4 ``check_forbidden_words``: one entry per matched ``FORBIDDEN_WORDS``
    entry present in the candidate name but not the track name. No dedup."""
    song = slugify(track.name).replace("-", "")
    cand = slugify(candidate.name).replace("-", "")
    return tuple(word for word in FORBIDDEN_WORDS if word in cand and word not in song)


def explicit_mismatch(track: Track, candidate: AudioCandidate) -> bool:
    """v4 explicit mismatch. ``AudioCandidate`` has no ``explicit`` field, so this
    is inert (``False``) unless a later plan adds one — read via ``getattr``."""
    candidate_explicit: bool | None = getattr(candidate, "explicit", None)
    return (
        track.explicit is not None
        and candidate_explicit is not None
        and track.explicit != candidate_explicit
    )


def isrc_equal(track: Track, candidate: AudioCandidate) -> bool:
    """True iff both ISRCs are present and equal after normalization
    (uppercase, hyphens stripped)."""
    if track.isrc is None or candidate.isrc is None:
        return False
    return track.isrc.upper().replace("-", "") == candidate.isrc.upper().replace("-", "")


def popularity_prior(candidate: AudioCandidate, *, max_popularity: float = 100.0) -> float:
    """Normalize candidate popularity to 0..1 (0.0 when unknown)."""
    if candidate.popularity is None:
        return 0.0
    return min(max(candidate.popularity / max_popularity, 0.0), 1.0)


def extract_features(track: Track, candidate: AudioCandidate) -> FeatureVector:
    """Assemble the ``FeatureVector`` by calling every feature once."""
    return FeatureVector(
        title_similarity=title_similarity(track, candidate),
        main_artist_similarity=main_artist_similarity(track, candidate),
        other_artist_similarity=other_artist_similarity(track, candidate),
        artist_similarity=artist_similarity(track, candidate),
        album_similarity=album_similarity(track, candidate),
        duration_delta_s=duration_delta_s(track, candidate),
        duration_similarity=duration_similarity(track, candidate),
        isrc_equal=isrc_equal(track, candidate),
        verified_source=candidate.verified,
        common_word_overlap=common_word_overlap(track, candidate),
        forbidden_words=forbidden_words(track, candidate),
        explicit_mismatch=explicit_mismatch(track, candidate),
        popularity_prior=popularity_prior(candidate),
    )
