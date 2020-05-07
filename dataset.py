from collections import OrderedDict
from pathlib import Path

import MeCab
import numpy as np
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tqdm import tqdm

MECAB_DIC_PATH = Path("/usr/local/lib/mecab/dic/mecab-ipadic-neologd")
DATA_URL = "https://www.rondhuit.com/download/ldcc-20140209.tar.gz"
DATA_PATH = Path("~/.keras/datasets/livedoor/livedoor.npz").expanduser()
TOKENIZER_PATH = Path("~/.keras/datasets/livedoor/tokenizer.json").expanduser()

CATEGORIES = OrderedDict(
    {
        # site_name: description
        "dokujo-tsushin": "独身女性",
        "it-life-hack": "IT",
        "kaden-channel": "家電",
        "livedoor-homme": "男性",
        "movie-enter": "映画",
        "peachy": "女性",
        "smax": "モバイル",
        "sports-watch": "スポーツ",
        "topic-news": "ニュース",
    }
)

LABELS = list(CATEGORIES.values())


class MeCabTokenizer:
    def __init__(self):
        if not MECAB_DIC_PATH.exists():
            raise RuntimeError(
                "MeCabTokenizer requires NEologd: "
                "https://github.com/neologd/mecab-ipadic-neologd"
            )

        self._mecab = MeCab.Tagger(f"-d {MECAB_DIC_PATH}")

    def tokenize(self, text):
        tokens = []

        for node in self._mecab.parse(text).split("\n"):
            if node in ["EOS", ""]:
                continue

            _surface, feature = node.split("\t")
            parts = feature.split(",")
            pos, lemma = parts[0:4], parts[6]

            if pos[0] not in ["名詞", "動詞", "形容詞"]:
                continue

            if pos[0:2] == ["名詞", "数"]:
                continue

            tokens.append(lemma)

        return " ".join(tokens)


def progress(iterable, *, desc=None):
    return tqdm(
        iterable,
        desc=desc,
        ncols=100,
        ascii=".=",
        bar_format="{n_fmt:3}/{total_fmt:3} [{bar:30}] - {desc}",
    )


def load_directory_data(directory, mecab):
    texts = []
    directory = Path(directory)
    site_name = directory.name
    txt_paths = list(
        filter(lambda x: x.name != "LICENSE.txt", directory.glob("**/*.txt"))
    )

    for txt_path in progress(txt_paths, desc=site_name):
        with txt_path.open() as txt:
            _site_url = next(txt)
            _wrote_at = next(txt)

            texts.append(mecab.tokenize(txt.read()))

    return texts


def save_data():
    tar_path = tf.keras.utils.get_file(
        "ldcc-20140209.tar.gz",
        DATA_URL,
        cache_subdir="datasets/livedoor",
        extract=True,
    )

    texts = []
    indices = []
    livedoor = Path(tar_path).parent
    mecab = MeCabTokenizer()

    for index, site_name in enumerate(CATEGORIES):
        directory = livedoor / "text" / site_name
        site_texts = load_directory_data(directory, mecab)
        texts += site_texts
        indices += [index] * len(site_texts)

    tokenizer = tf.keras.preprocessing.text.Tokenizer()
    tokenizer.fit_on_texts(texts)

    x = tokenizer.texts_to_sequences(texts)
    y = np.array(indices)

    with DATA_PATH.open("wb") as npz:
        np.savez(npz, x=x, y=y)

    with TOKENIZER_PATH.open("w") as json_file:
        json_file.write(tokenizer.to_json())


def load_data(test_split=0.2):
    if not DATA_PATH.exists():
        save_data()

    with np.load(DATA_PATH, allow_pickle=True) as npz:
        x = npz["x"]
        y = npz["y"]

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_split)

        return (x_train, y_train), (x_test, y_test)


def get_tokenizer():
    if not TOKENIZER_PATH.exists():
        save_data()

    with TOKENIZER_PATH.open("r") as json_file:
        return tf.keras.preprocessing.text.tokenizer_from_json(json_file.read())


def main():
    save_data()


if __name__ == "__main__":
    main()