#!/bin/bash
# Oracle for text-to-CAD tasks. Copying the held-back parametric reference to
# the answer path exercises the verifier alone and should score 1.0. A stub
# answer.py satisfies the declared artifact contract.
set -euo pipefail

cp /solution/reference.FCStd /app/answer.FCStd
printf '# oracle: answer produced by copying the held-back reference FCStd\n' > /app/answer.py

test -f /app/answer.py
test -f /app/answer.FCStd
