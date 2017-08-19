# Contributing to Bark

## How can I contribute?

Clone the repo locally, create a branch for the feature or bugfix, and start work!

```
$ git clone https://github.com/margoliashlab/bark
$ cd bark
$ git checkout -b awesome-feature
```

Before you submit a pull request, make sure the tests work. (If it makes sense to, write tests for your new feature, too.)

```
$ pytest -v
```

Then submit your PR!

Note! If you're a Margoliash lab member, don't merge your own pull request! Get somebody else to review your code first.

## Style guide

### Commit messages

There are lots of commit message best practices guides out there. Read one.

In general, though:

* write commit messages in imperative style (i.e.: "Fix #70" rather than "Fixes #70" or "Fixed #70").
* keep commit message subjects < 50 characters. More information, if necessary, can go in the body.
* write meaningful commit messages ("Fix #70" rather than "bluuuuuuhhhhhh").

It's apparently required by law to link to [this xkcd comic](https://xkcd.com/1296/). Don't write commit messages like that.

### Python code

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/).

### Documentation

Documentation lives in two places in the repository, depending on what it is.

Documentation on the usage of modules, functions, classes, and scripts lives in their docstrings. These should be formatted according to the [Google Python docstring guidelines](http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html). They are collected via Sphinx's `autodoc` extension and parsed by the `napoleon` extension.

Documentation on the repository as a whole, including installation, example usage and workflows, and other information not directly related to the code itself, lives in the `docs` folder, where it is built by Sphinx. It may be written in either [reStructuredText](http://docutils.sourceforge.net/docs/user/rst/quickref.html) or [(CommonMark-compatible) Markdown](http://commonmark.org/help/) (which is similar, but not quite identical, to Github-flavored Markdown).

The Sphinx-built documentation can be viewed online at [Read the Docs](http://bark.readthedocs.io/).

## Additional notes

This file is modeled on [Atom's contributing guidelines](https://github.com/atom/atom/blob/master/CONTRIBUTING.md).
