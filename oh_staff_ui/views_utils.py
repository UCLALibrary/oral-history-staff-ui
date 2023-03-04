from django.db.models import Q


def construct_keyword_query(query: str) -> Q:
    full_q = Q(title__icontains=query)
    keywords = query.split()
    for word in keywords:
        q_obj = Q(title__icontains=word)
        full_q = full_q | q_obj
    return full_q
