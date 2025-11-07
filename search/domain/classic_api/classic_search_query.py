# File: search/domain/classic_api/classic_search_query.py
# Desc: Where possible, adapt the parameter search_query,
#       into what the user probably intended.
#
# https://info.arxiv.org/help/api/user-manual.html
# The older perl/lucene implementation of the classic api allowed
#   search queries that did not match the api syntax,
#   yet would return a 200,
#   sometimes with no results,
#   sometimes with incorrect results.
#
# This python re-implementation validates input, and would otherwise reject
#   some of the queries users have become accustomed to.

import calendar
import re
from werkzeug.exceptions import BadRequest

def remove_charactors(search_query):
    if search_query:
        search_query = search_query.replace('\r', ' ').replace('\n', ' ')
    return search_query


def fix_aliases(q):
    if q:
        q = q.replace('lastUpdatedDate:','submittedDate:')
    return q


def fill_in_partial_dates(d, is_start=True):
    d1 = d
    try:
        if d.isdigit():
            if len(d) > 12:
                d = d[0:12]
            if len(d) == 6:
                if is_start:
                    d = f"{d}01"
                else:
                    y = int(d[0:4])
                    m = int(d[4:6])
                    day = calendar.monthrange(y,m)[1]
                    d = f"{d}{day}"
            if len(d) == 4:
                mmdd = "0101" if is_start else "1231"
                d = f"{d}{mmdd}"
            if len(d) == 8:
                hhmm = "0000" if is_start else "2359"
                d = f"{d}{hhmm}"
    except Exception as ex:
        d = d1
    return d


SD_RE = re.compile(r'submittedDate:\[([\d-]{4,14}) TO ([\d-]{4,14})\]')

def fix_dates(q):
    if q:
        result = ""
        last_end = 0
        for match in re.finditer(SD_RE, q):
            start, end = match.span()
            if start > last_end:
                result += q[last_end:start]

            d1 = fill_in_partial_dates(match.group(1), True)
            d2 = fill_in_partial_dates(match.group(2), False)
            result += f'submittedDate:"{d1} TO {d2}"'

            last_end = end

        if last_end < len(q):
            result += q[last_end:]

        q = result

    return q


# Documented prefixes:
#     https://info.arxiv.org/help/api/user-manual.html#51-details-of-query-construction
#     id_list is an http param
# Lucene prefixes vs Documented prefixes:
#     abs all au cat co date doi from grp id jr prim proxy rn sc subj submittedDate ti yr yymm
#     abs all au cat co                   id jr            rn         submittedDate ti


OPERATORS = 'AND ANDNOT NOT OR'.split()
OPERATORS_RE = '|'.join(OPERATORS)
OPERATORS_RE2 = r'\b(?:' + OPERATORS_RE + r')\b(?=[()\s]|$)'
PREFIXES1 = 'abs all au cat co doi id jr lastUpdatedDate rn submittedDate ti title'.split()
PREFIXES = [f"{f}:" for f in PREFIXES1]
PREFIXES_RE = "|".join(PREFIXES)

# the order is important:
TOKENS_RE = re.compile(fr'"[^"]*"|[()]|{OPERATORS_RE2}|{PREFIXES_RE}|[^"()\s]+')

def split_query_into_words(q):
    return TOKENS_RE.findall(q) if q else None

PREFIX       = 1
LEFT_PAREND  = 2
OPERATOR     = 3
RIGHT_PAREND = 4
TEXT         = 5

def tokenize(q):
    word_array = split_query_into_words(q)
    if word_array:
        tokens = []
        for word in word_array:
            if word in OPERATORS:
                tokens.append([OPERATOR, word])
            elif word in PREFIXES:
                tokens.append([PREFIX, word])
            elif word == '(':
                tokens.append([LEFT_PAREND, word])
            elif word == ')':
                tokens.append([RIGHT_PAREND, word])
            else:
                tokens.append([TEXT, word])
        return tokens if len(tokens) > 0 else None


# Probably run after other fixes.
def fix_missing_operators(tokens):
    if tokens:
        prev = None
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if ( prev != None and (
                (
                    prev[0] == PREFIX and
                    token[0] in [PREFIX]
                ) or (
                    prev[0] in [RIGHT_PAREND,TEXT] and
                    token[0] in [PREFIX, LEFT_PAREND, TEXT]
                )
            )):
                tokens.insert(i, [OPERATOR, "OR"])
                i = i + 1

            prev = token
            i = i + 1

    return tokens

def fix_author_underscores(tokens):
    if tokens:
        i = 0
        while i < len(tokens):
            if (
                i-1 >= 0 and
                tokens[i-1][0] == PREFIX and
                tokens[i][0] == TEXT
            ):
                s = tokens[1][1]
                if s.find("_") >= 0:
                    s = s.replace("_", " ")
                    if s.find('"') == -1:
                        s = f'"{s}"'
                    tokens[i][1] = s
            i = i+1

    return tokens

def fix_multiple_operators(tokens):
    if tokens:
        i = 0
        while i < len(tokens):
            if ( i-1 >= 0 and
                 tokens[i-1][0] == OPERATOR and
                 tokens[i][0] == OPERATOR
            ):
                del tokens[i-1]
                i = i - 1

            i = i + 1

    return tokens

def fix_missing_prefixes(tokens):
    if tokens:
        prev = None
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if ( token[0] == TEXT and
                 (prev == None or prev[0] != PREFIX)
            ):
                tokens.insert(i, [PREFIX, "all:"])
                i = i + 1
            prev = token
            i = i + 1

    return tokens


# Tempting, but won't do. Many log searches seem like phrases,
#   but would block users who really do want ORs
#def fix_missing_quotes(tokens):
#    return tokens


# Keep the outer parends, because an operator may follow.
# Fill in missing prefixes,
#   this is the main purpose of this method,
#   because each term inherits the outer prefix.
# Ignore operators.
# Check for nested parends.
# Probably ignore nested prefix-parends.
def fix_prefix_parends(tokens):
    if tokens:
        state = 0
        i = 0
        outer_prefix = None
        parend_count = 0
        while i < len(tokens):
            token = tokens[i]
            prev  = tokens[i-1] if i-1 >= 0 else None
            '''
            stateDiagram
                S0 --> S1 : prefix
                S1 --> S2 : (
                S2 --> S0 : )
            '''
            #print(f"i{i}, S{state},p{parend_count}:", [t[1] for t in tokens])
            if state == 0:
                if token[0] == PREFIX:
                    state = 1
                    outer_prefix = token[1]
            elif state == 1:
                # Delete the outer prefix
                if token[0] == LEFT_PAREND:
                    state = 2
                    del tokens[i-1]
                    i = i - 1
                    parend_count += 1
                else:
                    state = 0
            elif state == 2:
                if token[0] == RIGHT_PAREND:
                    parend_count -= 1
                    if parend_count == 0:
                        state = 0
                        outer_prefix = None
                elif token[0] == LEFT_PAREND:
                    parend_count += 1
                elif token[0] == TEXT:
                    # Add prefix if missing
                    if prev and prev[0] != PREFIX:
                        tokens.insert(i, [PREFIX, outer_prefix])
                        i = i + 1


            i = i + 1
    return tokens

def not_into_andnot(tokens):
    if tokens:
        prev = None
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if ( prev != None and
                 prev[0] == OPERATOR and
                 prev[1] == "AND" and
                 token[0] == OPERATOR and
                 token[1] == "NOT"
            ):
                del tokens[i-1]
                token[1] = "ANDNOT"
            elif ( token[0] == OPERATOR and
                   token[1] == "NOT"
            ):
                token[1] = "ANDNOT"

            prev = token
            i = i + 1

    return tokens


def convert_prefixes(tokens):
    if tokens:
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token[0] == PREFIX:
                if token[1] == "title:":
                    token[1] = "ti:"
            i = i + 1

    return tokens

def remove_prefixes_with_no_content(tokens):
    if tokens:
        i = 0
        while i < len(tokens):
            token = tokens[i]
            next1 = tokens[i+1] if i+1 < len(tokens) else None
            if ( token[0] == PREFIX and
                 ( next1 == None or (next1 != None and next1[0] != TEXT))
            ):
                del tokens[i]
                i = i - 1

            i = i + 1

    return tokens


def reformat(tokens):
    return (
        remove_prefixes_with_no_content(
        convert_prefixes(
        fix_author_underscores(
        fix_missing_operators(
        fix_multiple_operators(
        fix_missing_prefixes(
        fix_prefix_parends(
        not_into_andnot(
        tokens
    )))))))))

def tokens_into_query(tokens):
    arr = []
    prev = None
    if tokens:
        for tok in tokens:
            if not (
                (prev == None) or
                (prev[0] == LEFT_PAREND and tok[0] == PREFIX) or
                (prev[0] == TEXT        and tok[0] == RIGHT_PAREND) or
                (prev[0] == PREFIX      and tok[0] == TEXT)
            ):
                arr.append(" ")

            arr.append(tok[1])

            prev = tok

    return "".join(arr).strip() if len(arr)>0 else None

def adapt_query(q):
    try:
        result = (
            tokens_into_query(
            reformat(
            tokenize(
            fix_dates(
            fix_aliases(
            remove_charactors(
            q
        )))))))
        return result
    except Exception as ex:
        print(f"classic_search_query.adapt_query error: {ex}")
        raise BadRequest("Invalid search_query: {q}")
