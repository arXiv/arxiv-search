# Check pylint status
if [ -z ${MIN_SCORE} ]; then MIN_SCORE="8.5"; fi
PYLINT_SCORE=$( pipenv run pylint search | tail -2 | grep -Eo '[0-9\.]+/10' | tail -1 | sed s/\\/10// )
PYLINT_PASS=$(echo $PYLINT_SCORE">="$MIN_SCORE | bc -l)

if [ "$TRAVIS_PULL_REQUEST_SHA" = "" ];  then SHA=$TRAVIS_COMMIT; else SHA=$TRAVIS_PULL_REQUEST_SHA; fi
if [ $PYLINT_PASS -eq 1 ]; then PYLINT_STATE="success" &&  echo "pylint passed with score "$PYLINT_SCORE" for sha "$SHA; else PYLINT_STATE="failure" &&  echo "pylint failed with score "$PYLINT_SCORE" for sha "$SHA; fi

curl -u $USERNAME:$GITHUB_TOKEN \
    -d '{"state": "'$PYLINT_STATE'", "target_url": "https://travis-ci.com/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "'$PYLINT_SCORE'/10", "context": "code-quality/pylint"}' \
    -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA 


# Check mypy integration
MYPY_STATUS=$( pipenv run mypy -p search | grep -v "test.*" | grep -v "defined here" | tee /dev/tty | wc -l | tr -d '[:space:]' )
if [ $MYPY_STATUS -ne 0 ]; then MYPY_STATE="failure" && echo "mypy failed"; else MYPY_STATE="success" &&  echo "mypy passed"; fi

curl -u $USERNAME:$GITHUB_TOKEN \
    -d '{"state": "'$MYPY_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "", "context": "code-quality/mypy"}' \
    -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
    > /dev/null 2>&1


# Check pydocstyle integration
pipenv run pydocstyle --convention=numpy --add-ignore=D401,D202 search
PYDOCSTYLE_STATUS=$?
if [ $PYDOCSTYLE_STATUS -ne 0 ]; then PYDOCSTYLE_STATE="failure" && echo "pydocstyle failed"; else PYDOCSTYLE_STATE="success" &&  echo "pydocstyle passed"; fi

curl -u $USERNAME:$GITHUB_TOKEN \
    -d '{"state": "'$PYDOCSTYLE_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "", "context": "code-quality/pydocstyle"}' \
    -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
    > /dev/null 2>&1
