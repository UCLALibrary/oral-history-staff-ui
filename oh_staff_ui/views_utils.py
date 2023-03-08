from django.db.models import Q


def construct_keyword_query(query: str) -> Q:
    # Always include the full query, as a single substring.
    full_q = Q(title__icontains=query)
    keywords = query.split()
    # If there's only one word, it's the same as the full query, nothing to do.
    # Otherwise, grab the first word, then AND each following word.
    if len(keywords) > 1:
        words_q = Q(title__icontains=keywords[0])
        # All except the first word
        for word in keywords[1:]:
            words_q = words_q & Q(title__icontains=word)
        # OR the assembled set of words with the full query.
        full_q = full_q | words_q
    return full_q
