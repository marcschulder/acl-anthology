import re
from typing import Tuple, List, Set
from os import path
from nltk.corpus import stopwords, wordnet


def load_wordlist(filename: str) -> Tuple[Set[str], List[str]]:
    with open(filename) as f:
        comments = []
        lines = []
        for line in f:
            line = line.strip()
            if line.startswith('# '):
                comments.append(line)
            else:
                lines.append(line)
    return set(lines), comments


def filter_lowercaseable_words(words: Set[str], min_length: int = 1, verbose: bool = False) -> Set[str]:
    filtered_words = {"Bade", "Hung", "Rang", "Sera", "Soli", "Bled", "Imperia", "Central Nahuatl", "Min Nan Chinese",
                      "Min Dong Chinese", "T’bilisi", "St. Helens", "US Miscellaneous Pacific Islands", "MIMAROPA",
                      "Macao SAR", "Hong Kong SAR", "CALABARZON", "Arab Republic of Egypt", "Cocos Islands Malay",
                      "German Democratic Republic", "Min Bei Chinese", "Min Zhong Chinese", "Interlingua",
                      "Interlingue", "Interglossa", "Sur", "Notre", "Meta'", "Meta", "Amo", "Lingua Franca", "Tera",
                      "Au", "Multiple languages", "Nord", "Ouest", "Uma", "Portuguesa", "Est", "Sar", "wallonne",
                      "Isle of Anglesey; Sir Ynys Môn", "Attorneys"}
    stopws = set(stopwords.words('english'))
    # re.compile(r'(()|())()')

    always_caps_words = set()
    word2false_alarms = {}
    for word in sorted(words):
        false_alarms = []
        is_always_caps = True

        for x in ['Bay', 'Coast', 'Gulf', 'Island', 'Isle', 'Lake', 'Republic', 'University']:
            xofthe = f'{x} of the '
            xof = f'{x} of '
            yx = f' {x}'
            if word.startswith(xofthe):
                word = word[len(xofthe):]
                break
            elif word.startswith(xof):
                word = word[len(xof):]
                break
            elif word.endswith(yx):
                word = word[:-len(yx)]
                break

        def drop_adj(adjword):
            for adj in ['North',
                        'South',
                        'East',
                        'West',
                        'Northeast',
                        'Northwest',
                        'Southeast',
                        'Southwest',
                        'Central',
                        'Northern',
                        'Southern',
                        'Eastern',
                        'Western',
                        'Northeastern',
                        'Northwestern',
                        'Southeastern',
                        'Southwestern',
                        'Modern',
                        'Ancient']:
                amod = f'{adj} '
                if adjword.startswith(amod):
                    adjword = adjword[len(amod):]
                    return drop_adj(adjword)
            return adjword

        word = drop_adj(word)

        if len(word) < min_length:
            is_always_caps = False

        if any([c in word for c in '-!/ǂ()[]']):
            is_always_caps = False
        if word[0] in "'’":
            is_always_caps = False
        if len(word) > 1 and word[1] in "'’":
            is_always_caps = False

        if all([any([c.isupper() for c in w[1:]]) for w in word.split(' ')]):
            print(word)
            is_always_caps = False

        if word.lower() in stopws:
            is_always_caps = False
        if word in filtered_words:
            is_always_caps = False

        if is_always_caps:
            for synset in wordnet.synsets(word):
                for lemma in synset.lemmas():
                    lemma_name = lemma.name()

                    is_genus = lemma_name.startswith('genus_')
                    is_place = lemma_name.startswith('capital_of_')
                    if is_genus or is_place:
                        continue

                    if lemma_name[0].islower():
                        lemma_is_word_start = word.lower().startswith(lemma_name.lower())
                        word_part_of_mwe_lemma = '_' in lemma_name and word in lemma_name.split('_')

                        if lemma_is_word_start or word_part_of_mwe_lemma:
                            is_always_caps = False
                            # if verbose:
                            #     print(word, '-', lemma_name, '-', synset.definition())
                        else:
                            false_alarms.append((lemma_name, synset.definition()))
                            # if verbose:
                            #     print(word, 'X', lemma_name)
                    # elif verbose:
                    #     print(word, '=', lemma_name)

                    # if not is_always_caps:
                    #     break
                if not is_always_caps:
                    break
            if is_always_caps and false_alarms:
                word2false_alarms[word] = false_alarms

        if is_always_caps:
            always_caps_words.add(word)

    # if verbose:
    #     for word, false_alarms in word2false_alarms.items():
    #         print(word)
    #         for lemma_name, synset_definition in false_alarms:
    #             print(f'  {lemma_name} -> {synset_definition}')
    #             # print(lemma_name)

    return always_caps_words


truelist, truecomments = load_wordlist('truelist')

capspath = '../../../../publications/meta_lrec_bibliography/capitalisation_whitelists/'
languages, _ = load_wordlist(path.join(capspath, 'languages.txt'))
extralanguages, _ = load_wordlist('Languages.-.other.txt')
countries, _ = load_wordlist(path.join(capspath, 'countries.txt'))
regions, _ = load_wordlist(path.join(capspath, 'regions.txt'))
subdivisions, _ = load_wordlist(path.join(capspath, 'subdivisions.txt'))
other, _ = load_wordlist('LREC.SignLang.-.other.txt')

# english_vocab = set(words.words())
# stopwords = set(stopwords.words('english'))
# wordnet_vocab = set([w.replace('_', ' ') for w in wordnet.words()])

#%%
# print("Truelist:  ", len(truelist))
# print("+languages:", len(truelist | languages) - len(truelist))
# print("+extralang:", len(truelist | extralanguages) - len(truelist))
# print("+countries:", len(truelist | countries) - len(truelist))
# print("+regions:  ", len(truelist | regions) - len(truelist))
# print("+subdivs:  ", len(truelist | subdivisions) - len(truelist))
# print("+other:    ", len(truelist | other) - len(truelist))

#%%
min_len = 2
v = True
print("Minimum length:", min_len)
print("### Languages")
clear_languages = filter_lowercaseable_words(languages, min_length=min_len, verbose=v)
print("\n### Extra Languages")
clear_extralanguages = filter_lowercaseable_words(extralanguages, min_length=min_len, verbose=v)
print("\n### Countries")
clear_countries = filter_lowercaseable_words(countries, min_length=min_len, verbose=v)
print("\n### Regions")
clear_regions = filter_lowercaseable_words(regions, min_length=min_len, verbose=v)
print("\n### Subdivisions")
clear_subdivisions = filter_lowercaseable_words(subdivisions, min_length=min_len, verbose=v)
# print("\n### Other")
# clear_other = filter_lowercaseable_words(other, min_length=min_len, verbose=v)
print("\n\n### Results")
print("languages:", len(languages), '->', len(clear_languages))
print("extralang:", len(extralanguages), '->', len(clear_extralanguages))
print("countries:", len(countries), '->', len(clear_countries))
print("regions:  ", len(regions), '->', len(clear_regions))
print("subdivs:  ", len(subdivisions), '->', len(clear_subdivisions))
# print("other:    ", len(other), '->', len(clear_other))
print("other:    ", len(other))
print()

#%%
# min_len = 4
# print("Minimum length:", min_len)
# print("languages:", len(languages), '->', len(filter_lowercaseable_words(languages, min_length=min_len)))
# print("extralang:", len(extralanguages), '->', len(filter_lowercaseable_words(extralanguages, min_length=min_len)))
# print("countries:", len(countries), '->', len(filter_lowercaseable_words(countries, min_length=min_len)))
# print("regions:  ", len(regions), '->', len(filter_lowercaseable_words(regions, min_length=min_len)))
# print("subdivs:  ", len(subdivisions), '->', len(filter_lowercaseable_words(subdivisions, min_length=min_len)))
# print("other:    ", len(other), '->', len(filter_lowercaseable_words(other, min_length=min_len)))
# print()
#
# #%%
# min_len = 5
# print("Minimum length:", min_len)
# print("languages:", len(languages), '->', len(filter_lowercaseable_words(languages, min_length=min_len)))
# print("extralang:", len(extralanguages), '->', len(filter_lowercaseable_words(extralanguages, min_length=min_len)))
# print("countries:", len(countries), '->', len(filter_lowercaseable_words(countries, min_length=min_len)))
# print("regions:  ", len(regions), '->', len(filter_lowercaseable_words(regions, min_length=min_len)))
# print("subdivs:  ", len(subdivisions), '->', len(filter_lowercaseable_words(subdivisions, min_length=min_len)))
# print("other:    ", len(other), '->', len(filter_lowercaseable_words(other, min_length=min_len)))
# print()

#%%
sign_languages = clear_extralanguages | {sl for sl in clear_languages if "Sign Language" in sl}

entries = clear_languages | clear_extralanguages | clear_countries | clear_regions | clear_subdivisions | other
new_entries = entries - truelist

new_entries_mweclean = {e for e in new_entries if any(x not in truelist for x in e.split(' '))}

print(len(entries), len(new_entries), len(new_entries_mweclean))

# with open('../../data/xml/foobar.xml', 'w') as w:
#     w.write("""<?xml version='1.0' encoding='UTF-8'?><collection id="1991.iwpt"><volume id="1" ingest-date="2020-05-11"><meta><booktitle>Proceedings of the Second International Workshop on Parsing Technologies</booktitle></meta>\n""")
#     for i, entry in enumerate(sorted(new_entries_mweclean)):
#         w.write(f'<paper id="{i}"><title>Paper about {entry} for science</title></paper>\n')
#     w.write("""</volume></collection>""")

with open('truelist', 'w') as w:
    w.write("""# Automatically generated by train.py
# and hand-corrected
# Incorporates language/script names from https://en.wikipedia.org/wiki/List_of_language_names
""")
    for entry in sorted(truelist | new_entries_mweclean):
        w.write(f'{entry}\n')
