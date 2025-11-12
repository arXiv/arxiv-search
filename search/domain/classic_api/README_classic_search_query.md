# README_classic_search_query.md

- These are tests of the perl/lucene search syntax on exports.
- In a few cases, curl-localhost is shown, which is the python replacement.

## How to Test
- Check the search results for how query is parsed: ArXiv Query
- Spaces: ok to use + or %20
- Quotes: getting lost in my bash shell, use %22
- Braces: encode [ ] as: %5B %5D
- Asterisk: %2A
- Parends: maybe ok to escape: \( \), or: %28 %29
```

curl -is https://export.arxiv.org/api/query\?search_query\=\(ti:a+AND+ti:b\) | gi '<title' | sort
```


## How do Missing Operators Work
- Defaults to OR

Details:
- search for: pineapple, because it's not common.
- search for: space, because it is common.
- Still finds in title search: spacings, spaces, pineAPPL
- Bug? Using all:(...) only gave 1 result
- Bug? No prefix or parends gave 5 results


#### notarealword space
- Bug? There's only 5 results... No, now it's working.
- 10 results with space.
- So OR is configured as the default.
```
curl -is https://export.arxiv.org/api/query\?search_query\=notarealword+space | gi '<title' | sort
```
#### notarealword1 notarealword2
- No results
```
curl -is https://export.arxiv.org/api/query\?search_query\=notarealword1+notarealword2 | gi '<title' | sort
```


#### ti:(notarealword pineapple)
- This is an OR.
- pineapple is present in all titles
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(notarealword+pineapple\) | gi '<title' | sort

curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(notarealword+space\) | gi '<title' | sort
```

#### ti:(hawaii OR pineapple)
- An OR, sometimes either in title.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(%22hawaii+OR+pineapple%22\) | gi '<title' | sort
    <title>On the spectral redundancy of pineapple graphs</title>
    <title>SCUBA observations of Hawaii 167</title>
    ...
```

#### ti:(notarealword OR pineapple)
- Same results as above, without the OR
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(notarealword+OR+pineapple\) | gi '<title' | sort
```


#### ti:(notarealword AND pineapple)
- No results
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(notarealword+AND+pineapple\) | gi '<title' | sort
```

#### ti:(notarealword and pineapple)
- An OR of the 3 words
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(notarealword+and+pineapple\) | gi '<title' | sort
```

#### ti:(notarealword "pineapple")
- Adding quotes does not make it literal, still finds pineappl
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(notarealword+%22pineapple%22\) | gi '<title' | sort
```


## How Do Prefix Parends Work
- Meaning, a parend between the prefix and search-text
- Can wrap prefix:terms
- Can wrap boolean expressions.
- Can follow prefixes, ti:(...)
- The prefix is carried through to all terms, and defaults to OR.

#### ti:(space time)
- an OR.
- at least one of space OR time must be present in the title.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(space+time\) | gi '<title' | sort

curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28space+time%29 | gi '<title' | sort
```


#### ti:(space AND (apple OR time))
- 10 results, all space and time
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28space+AND+%28apple+OR+time%29%29 | gi '<title' | sort
```

#### ti:(space AND (apple OR pineapple))
- 2 results, space and apple/appl
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28space+AND+%28apple+OR+pineapple%29%29 | gi '<title' | sort
    apple core in the recorded frequency space</title>
    Banach spaces" [J. Math. Anal. Appl.</title>
```

#### ti:(space AND time) OR ti:apple
- grouping seems broken in old lucene, 3 results?... I think a server issue.
- 10 result now.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28space+AND+time%29+OR+ti:apple | gi '<title' | sort
```

#### ti:(space AND time) OR apple
- all space-time results
- slightly different because apple can be found anywhere.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28space+AND+time%29+OR+apple | gi '<title' | sort
```

#### ti:((space AND time) OR ti:apple)
- 10 apple results.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28%28space+AND+time%29+OR+ti:apple%29 | gi '<title' | sort
```

#### ti:(NOT space AND time)
- 10 time.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28NOT+space+AND+time%29 | gi '<title' | sort
```
)
#### ti:(ti:space)
- 10 space.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28ti:%28space%29%29 | gi '<title' | sort
```

#### au:(space AND ti:time)
- 5 titles with time, author seems ignored.
```
curl -is https://export.arxiv.org/api/query\?search_query\=au:%28space+AND+ti:time%29 | egrep '<title|<name'
```

#### ti:(space AND au:time)
- 1 titles with space and time, author has time.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28space+AND+au:time%29 | egrep '<title|<name'
    <title>Space-time distributions</title>
    <name>Mihaela Time</name>

```



#### (ti:(space AND time) OR ti:apple)
- Same results as above. The parends are slightly diffent.
```
curl -is https://export.arxiv.org/api/query\?search_query\=%28ti:%28space+AND+time%29+OR+ti:apple%29 | gi '<title' | sort
```

#### (ti:(space AND time) OR apple)
- all space and time results.
- same results when no outer parends.
```
curl -is https://export.arxiv.org/api/query\?search_query\=%28ti:%28space+AND+time%29+OR+apple%29 | gi '<title' | sort
```

#### ti:space AND ti:time OR ti:apple
- Mostly space and time results, but different from above.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:space+AND+ti:time+OR+ti:apple | gi '<title' | sort
```

#### (ti:space AND ti:time) OR ti:apple
- Mostly apple results, strange that it's not space and time.
```
curl -is https://export.arxiv.org/api/query\?search_query\=%28ti:space+AND+ti:time%29+OR+ti:apple | gi '<title' | sort
```

## Nested prefix-parends
#### all:(title:(apple))
- No results
```
curl -is https://export.arxiv.org/api/query\?search_query\=all:%28title:%28apple%29%29 | gi '<title' | sort
```



## How Do Prefix Parends and Quotes Work
- They are phrases, the words should be found together.

#### ti:("hawaii pineapple")
- This is a phrase, finds 1 result, both in sequence in the title
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(%22hawaii+pineapple%22\) | gi '<title' | sort
```

#### ti:("hawaii pineapple" AND matrix)
- This is a phrase and an additional word in the title.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(%22hawaii+pineapple%22+AND+matrix\) | gi '<title' | sort
    <title>MATRIX HAWAII: PineAPPL ...
```

#### ti:("hawaii pineapple" AND notarealword)
- No results
- This is a phrase and an additional word in the title.
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(%22hawaii+pineapple%22+AND+notarealword\) | gi '<title' | sort
```

#### ti:("hawaii OR pineapple")
- No results
- This is a phrase, and OR is not an operator
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(%22hawaii+OR+pineapple%22\) | gi '<title' | sort
```



## How Do Quotes Work
- They are phrases, the words should be found together.

#### ti:"pineapple"
- Found in title
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%22pineapple%22 | gi '<title' | sort
```

#### ti:"pineapple" "apices"
- An OR
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%22pineapple%22+%22apices%22 | gi '<title' | sort
```

#### ti:"pineapple" ti:"apices"
- An OR
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%22pineapple%22+ti:%22apices%22 | gi '<title' | sort
```



## How does Grouping Work
- Incorrect: Precedence is left to right, in lucene 1.2 (pre-2002)
- No, we're using lucene 2.3.2
- So precidence is AND, then OR

#### ti:pineapple matrix AND ti:pineapple
- Finds 2 result, 1 has matrix in the abstract.
```
curl -si https://export.arxiv.org/api/query\?search_query\=ti:pineapple+matrix+AND+ti:pineapple | egrep '<title'
```

#### ti:pineapple AND ti:pineapple OR matrix
- Finds 10 results, all have pineapple in title.
```
curl -si https://export.arxiv.org/api/query\?search_query\=ti:pineapple+AND+ti:pineapple+OR+matrix | egrep '<title'

same if the OR is removed:
curl -si https://export.arxiv.org/api/query\?search_query\=ti:pineapple+AND+ti:pineapple+matrix | egrep '<title'
```

#### ti:pineapple AND matrix OR ti:pineapple
```
curl -si https://export.arxiv.org/api/query\?search_query\=ti:pineapple+AND+matrix+OR+ti:pineapple | egrep '<title'

same if the OR is removed:
curl -si https://export.arxiv.org/api/query\?search_query\=ti:pineapple+AND+matrix+ti:pineapple | egrep '<title'
```



## How to Search for Authors

#### del Maestro
- Multi-last names
- All work: an underscore or space, and quoting.
```
curl -si https://export.arxiv.org/api/query\?search_query\=au:del+maestro | egrep '<name|<title'
curl -si https://export.arxiv.org/api/query\?search_query\=au:%22del+maestro%22 | egrep '<name|<title'
curl -si https://export.arxiv.org/api/query\?search_query\=au:del_maestro | egrep '<name|<title'
curl -si https://export.arxiv.org/api/query\?search_query\=au:%22del_maestro%22 | egrep '<name|<title'

curl -si http://localhost:8080/api/query\?search_query\=au:%22del_maestro%22 | egrep '<name|<title'
```

#### au:del_mae*
- underscore is a shortcut for quotes and spaces.
- wildcards work
```
curl -si https://export.arxiv.org/api/query\?search_query\=au:del_mae%2A | egrep '<name|<title'
```

#### all:*
- No results
```
curl -si https://export.arxiv.org/api/query\?search_query\=all:%2A | egrep '<title'
```

#### *
- Query cannot start with a wildcard
```
curl -is http://localhost:8080/api/query\?search_query\=%2A'
```

## Bypass search query adaptor
#### pineapple &raw=1
- Error
```
curl -is http://localhost:8080/api/query\?search_query\=pineapple\&raw\=1
  <entry>
    <title>Error</title>
    <summary>Invalid query string: 'pineapple'</summary>
```
#### pineapple
- Works, see first title elemeent for changes made.
```
curl -is http://localhost:8080/api/query\?search_query\=pineapple\&raw\=1
    ...
    <title>arXiv Query: search_query=all:pineapple
```



## How to Search for Multiple Categories

#### cat:q-fin.*
```
# Works:
curl -si https://export.arxiv.org/api/query\?search_query\=cat:q-fin.%2A | egrep 'cat|<title'

# Fails:
curl -si http://localhost:8080/api/query\?search_query\=cat:q-fin.%2A | egrep 'cat|<title'
```

#### ti:"Periodicity in Cryptocurrency Volatility and Liquidity" AND cat:q-fin.PR
```
curl -si https://export.arxiv.org/api/query\?search_query\=ti:%22Periodicity+in+Cryptocurrency+Volatility+and+Liquidity%22+AND+cat:q-fin.PR | gi '<title|category|<id>'
    <id>... 2109.12142v2

# Also works: q-fin.TR
# Does not works if cs.SD
# Also works: cat:q-fin.%2A

curl -si http://localhost:8080/api/query\?search_query\=ti:%22Periodicity+in+Cryptocurrency+Volatility+and+Liquidity%22+AND+cat:q-fin.PR | gi '<title|category|<id>'
# Also works: q-fin.TR
curl -si http://localhost:8080/api/query\?search_query\=ti:%22Periodicity+in+Cryptocurrency+Volatility+and+Liquidity%22+AND+cat:q-fin.PR | gi '<title|category|<id>'# Does not works: q-fin.%2A
```

#### cat:q-fin.* AND submittedDate:"201602070000 TO 201602072359"
```
curl -si http://localhost:8080/api/query\?search_query\=cat:q-fin.%2A+AND+submittedDate:%22201602070000+TO+201602072359%22 | gi '<title|category|<id>'
```



## Dates
```
curl -is http://localhost:8080/api/query\?search_query\=submittedDate:\"202301010600+TO+202301030600\" | egrep -i 'date|publish|<id>'

Same with [ ]:
http://localhost:8080/api/query\?search_query\=submittedDate:%5b202301010600+TO+202301030600%5D | egrep -i '<id>' | sort
   ...
   <id>http://arxiv.org/abs/2210.05489v3</id>
   <updated>2023-01-02T20:15:04Z</updated>
   <published>2022-10-11T10:45:07Z</published>

So, updated is when the last paper version was created,
and published is when the first paper version was created.


select paper_id, version, created, updated from arXiv_metadata where paper_id in ('2207.13988', '2001.00440', '2207.08847', '2210.05489', '2210.13535', '2211.10532', '2208.12182', '2208.12234', '2208.05473') order by 1,2;
+------------+---------+---------------------+---------------------+
| paper_id   | version | created             | updated             |
+------------+---------+---------------------+---------------------+
| 2210.05489 |       1 | 2022-10-11 14:45:07 | 2022-10-12 00:17:33 |
| 2210.05489 |       2 | 2022-12-01 20:06:33 | 2022-12-05 01:01:12 |
| 2210.05489 |       3 | 2023-01-02 05:37:45 | 2023-01-03 01:15:04 |
+------------+---------+---------------------+---------------------+

# legacy:
curl -si https://export.arxiv.org/api/query\?search_query\=ti:%22Generating+Approximate+Ground+States+of+Molecules%22 | gi '<updated|<publish|<id>'
  <updated>2025-11-03T00:00:00-05:00</updated>
    <id>http://arxiv.org/abs/2210.05489v3</id>
    <updated>2023-01-02T05:37:45Z</updated>
    <published>2022-10-11T14:45:07Z</published>

curl -si https://export.arxiv.org/api/query\?search_query\=ti:%22Generating+Approximate+Ground+States+of+Molecules%22+AND+submittedDate:%5b202301010600+TO+202301030600%5D | gi '<updated|<publish|<id>'

curl -si https://export.arxiv.org/api/query\?search_query\=ti:%22Generating+Approximate+Ground+States+of+Molecules%22+AND+submittedDate:%5b202210100600+TO+202210120600%5D | gi '<updated|<publish|<id>'
    ...
    <id>http://arxiv.org/abs/2210.05489v3</id>

So, submittedDate searches the value in the published xml element.

# Correct the python search to use published:
curl -si http://localhost:8080/api/query\?search_query\=ti:%22Generating+Approximate+Ground+States+of+Molecules%22+AND+submittedDate:%5b202210100600+TO+202210120600%5D | gi '<updated|<publish|<id>|<title'
    <id>http://arxiv.org/abs/2210.05489v3</id>
    <updated>2025-11-03T18:00:21Z</updated>
    <published>2022-10-11T10:45:07Z</published>
    <title>Generating Approximate Ground States of Mol...

# also works: [] and lastUpdatedDate
curl -si http://localhost:8080/api/query\?search_query\=ti:%22Generating+Approximate+Ground+States+of+Molecules%22+AND+lastUpdatedDate:%5B202210100600+TO+202210120600%5D | gi '<updated|<publish|<id>|<title'
curl -si http://localhost:8080/api/query\?search_query\=ti:%22Generating+Approximate+Ground+States+of+Molecules%22+AND+lastUpdatedDate:%22202210100600+TO+202210120600%22 | gi '<updated|<publish|<id>|<title'
```



## Undocumented
- asterisk=%2A
#### doi:
```
# no results:
curl -is https://export.arxiv.org/api/query\?search_query\=doi:%2210.1088%2F0004-637X%2F753%2F1%2F35%22

works, quotes optional:
curl https://export.arxiv.org/api/query\?search_query\=doi:%2210.1038/418838a%22 | gi 0204030
curl https://export.arxiv.org/api/query\?search_query\=doi:10.1038/418838a

# asterisk works without quotes:
curl https://export.arxiv.org/api/query\?search_query\=doi:10.1038/418838a%2A
```
- v2: all finds dois, works with/without quotes
```
curl -si http://localhost:8080/api/query\?search_query\=all:%2210.1038/418838a%22
curl -si http://localhost:8080/api/query\?search_query\=doi:%2210.1038/418838a%22
```

## Modifiers
#### ti:(apple OR matrix^5)
- Was finding apple, now all matrix
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28apple+OR+%22matrix%22\^5%29 | gi '<title' | sort
```

#### ~
- Seems to work on author and all prefixes, but not title
- Seems to have no effect.
```
curl -si https://export.arxiv.org/api/query\?search_query\=%22fruit+identification%22\~3 | egrep '<name|<title'

curl -si https://export.arxiv.org/api/query\?search_query\=%22fruit+identification%22\~3 | egrep '<name|<title'
```

## Invalid
- Queries that are accepted by lucene, but don't return results, or don't make sense in some way.

#### ti:(AND AND AND)
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:\(AND+AND+AND\)
```

#### ti:(a AND AND AND b)
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28a+AND+AND+AND+b%29 | gi '<title'

# opposed to this, with lots of results:
curl -is https://export.arxiv.org/api/query\?search_query\=ti:%28a+AND+b%29 | gi '<title'
```

#### a AND AND AND b
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=a+AND+AND+AND+b
```

#### all:("pineapple"
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=all:%28%22pineapple%22
```

#### (ti:space
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=%28ti:space
```


#### ti:pineapple+AND+au:
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=ti:pineapple+AND+au:

# But does work if quotes are added, ie: au:""
```

#### au:""
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=au:%22%22
```

#### all:ti:"pineapple"
- success, but no results
```
curl -is https://export.arxiv.org/api/query\?search_query\=all:ti:%22pineapple%22
```

#### all:请检索并总结近几年
- fails on non-english
```
curl -is https://export.arxiv.org/api/query\?search_query\=all:ti:请检索并总结近几年
```


## Lucene Source
- https://svn.apache.org/repos/asf/lucene/java/tags/lucene_1_2_final/src/java/org/apache/lucene/queryParser/QueryParser.jj
- So old, not in the archive subfolder:
https://archive.apache.org/dist/lucene/java/archive/
- But that's not the version in place now...
```
cd arxiv-httpd/java/lucene_search
grep lucene build.xml
    <exclude name="lucene-1.2.jar"/>

cd arxiv-httpd/java/lucene_search/lib
jar xf lucene.jar META-INF/MANIFEST.MF
cat META-INF/MANIFEST.MF | grep Implementation-Version
    Implementation-Version: 2.3.2 652650 - buschmi - 2008-05-01 13:30:57
```

## Some more changes on 2025-11-12
- https://groups.google.com/a/arxiv.org/g/api

#### updated element is created for the most recent paper_version
```
+-----------+---------+---------------------+---------------------+
| paper_id  | version | created             | updated             |
+-----------+---------+---------------------+---------------------+
| 1212.1873 |       1 | 2012-12-09 10:12:37 | 2012-12-11 01:01:49 |
| 1212.1873 |       2 | 2012-12-13 16:03:09 | 2012-12-14 01:02:40 |
| 1212.1873 |       3 | 2012-12-19 15:36:05 | 2012-12-20 01:02:52 |
| 1212.1873 |       4 | 2013-01-03 21:33:39 | 2013-01-07 01:00:28 |
| 1212.1873 |       5 | 2013-07-24 09:15:36 | 2013-07-25 00:04:29 |
| 1212.1873 |       6 | 2014-01-29 08:13:51 | 2014-09-23 00:12:27 |

# Wrong one:
curl -si http://localhost:8080/api/query\?id_list\=1212.1873 | grep updated
    <updated>2014-09-22T20:12:27Z</updated>
Instead send current submitted date:
    <updated>2014-01-29T03:13:51Z</updated>

# Test new submission:
| paper_id   | version | created             | updated             |
| 2511.07430 |       1 | 2025-10-30 05:59:48 | 2025-11-12 01:00:22 |
curl -si http://localhost:8080/api/query\?id_list\=2511.07430 | gi updated
    <updated>2025-10-30T01:59:48Z</updated>


```
