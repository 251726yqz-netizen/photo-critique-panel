# Test imagery

The six valid PNG scenes and the two intentionally invalid files in this directory
are original test data, dedicated to the public domain under CC0 1.0:
https://creativecommons.org/publicdomain/zero/1.0/

They are **synthetic illustrations, not photographs or documentary evidence**.
They test observation boundaries, role distinctions and instruction handling.
They cannot establish performance on real photography or university applications.

Generation source for the valid scenes: ../make_fixtures.py. Images contain no EXIF camera metadata.

`unreadable.png` contains a short plain-text invalid PNG payload; `unreadable.pdf`
has a PDF header followed by intentionally truncated data and no page objects.
They are failure fixtures, not hidden pictures or user documents.
