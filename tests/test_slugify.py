
import pytest

from utilities.utils import slugify

@pytest.mark.parametrize(
    ('input_text', 'expected'),
    [
        (' www.mdp.com ', 'www_mdp_com'), 
        (' www.#mdp.com ', 'www_mdp_com'),
        ('www.árabesco.com', 'www_arabesco_com')
    ]
)

def test_slugify(input_text, expected):
    result = slugify(input_text)
    assert result == expected



