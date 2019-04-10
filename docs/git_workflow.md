# Margoliash lab git and github workflow and guidelines

## General principles

1. All development should take place in dedicated branches.
2. The **only** commits made to your `master` branch should be merges from other forks (presumably, mostly from `margoliashlab`).
3. Write and run tests. Some code (particularly I/O) can be hard or impossible to properly test; omitting tests for such code should be a careful and deliberate decision.
4. Follow up on pull requests - you aren't done once you hit "Create pull request". There may be multiple rounds of review and requested or debated changes.
5. All pull requests should be reviewed by at least one person. This really helps cut down on bugs.

## Instructions for common operations

All of these instructions are written using the command-line `git` tools.

### when you begin work on a new feature or bugfix of an existing repository

We'll pretend the repository is named `testrepo`.

1. Clone the repo onto your local machine and `cd` into it.
    ```
    $ git clone https://github.com/margoliashlab/testrepo.git
    $ cd testrepo
    ```
2. Create a new branch for your feature or bugfix. We'll call our new branch "testbranch".
    ```
    $ git branch testbranch
    $ git checkout testbranch
    ```
    Or you can combine both of those operations into a single command:
    ```
    $ git checkout -b testbranch
    ```
3. Begin working.

### update your local copy of the repo

There may have been changes made to the margoliashlab `master` branch while you were working. To make sure your local copy is up-to-date:

1. Make sure you're on your local `master` branch.
    ```
    $ git checkout master
    ```
2. Merge new commits from the margoliashlab `master` branch into your local `master` branch.
    ```
    $ git pull margoliashlab master
    ```

If you've kept your repo and branch organization tidy, by following this guide, this procedure should be painless and automatic.

### incorporate changes from your local `master` branch into your new branch

Once you've merged changes from margoliashlab/master into your local master, you also need to incorporate changes into your new branch. This will involve a rebase, rather than a merge.

1. Make sure you're on your new branch.
    ```
    $ git checkout testbranch
    ```
2. Rebase your branch onto the new local master branch.
    ```
    $ git rebase master
    ```

If `git` determines that this operation can be done automatically, it will do so, and you'll be done. However, if changes you've made in your new branch conflict with changes made to your `master` branch, you'll need to resolve the conflicts manually, by opening the files `git` mentions and deciding which version to keep (the rebase will have inserted some information into the files to help you decide). Once you resolve a round of conflicts, you need to commit your changes, and then continue the rebase with
```
$ git rebase --continue
```
This will continue the rebase already in progress. It's possible that the rebase will encounter further conflicts. Resolve them, commit the changes, and continue the rebase as already described until you're done.

### when you're done writing your new branch

Let's say you've finished writing a new feature, or you've successfully fixed a bug. Now you want to merge your changes into the margoliashlab `master` branch, so other lab members can use it.

1. Make sure the tests run.
    ```
    $ pytest -v
    ```
    The Travis CI service will run the tests when you submit a pull request, but making sure before you submit is a good idea.
2. If there have been changes to the margoliashlab `master` branch while you were working, you may want to incorporate them into your branch before you submit a pull request. However, if none of the files you modified were changed on the margoliashlab `master` branch, you probably won't need to do this - `git` is smart enough to figure that out, based on commit timestamps. If you do need to update your local copy of the repo, follow the instructions elsewhere in this guide to merge them into your `master` branch and rebase your new branch on top of them.
3. Update your repo on Github. (This command assumes your Github copy of this repo is configured to be a remote called "origin".)
    ```
    $ git push origin testbranch
    ```
    Note that you're pushing to `testbranch` on Github, **not** `master`! If `testbranch` doesn't already exist on Github, `git` will create it.
4. Submit a pull request via the Github website. Make sure you're choosing the correct base and head forks and branches. It's also a very good idea to examine the commits and files that Github thinks should be included in the pull request **before** you hit the "Create pull request" button. This will often clue you in to errors you may be about to make - comparing across the wrong fork or branch, or forgetting to update your `.gitignore` to exclude some file that you needed during development but doesn't belong in the repo itself.
5. Whatever you do, **do not approve your own pull request**. Get somebody else to do it, after they look over the changes you made. This is not something that only newbies have to do - getting a second pair of eyes to look over your work is useful for developers of every level of experience. If there's someone you think is particularly appropriate to review your pull request, you can request that they do so when you submit it.
6. Address any questions, concerns, or requested changes to your pull request that the reviewer brings up. Unless you do this, your work won't be incorporated into the margoliashlab repo, and other lab members won't be able to use it.

### post-merge cleanup

Once your pull request has been approved and merged (likely via a squash-merge) into the margoliashlab repo, there are a couple of little bits of tidying-up to do:

1. If you're done working on your new feature or bugfix, you can delete the branch from your local repository.
    ```
    $ git checkout master
    $ git branch -D testbranch
    ```
    Don't worry about losing work - it's already a part of the margoliashlab `master` branch. And definitely **do not** merge your branch back into your local `master`.
    You can also delete the branch on your Github repo. You can either do this on the Github website, or on the command line:
    ```
    $ git push origin --delete testbranch
    ```
2. Merge the changes to margoliashlab `master` into your local `master`, following the instructions elsewhere in this guide. This now brings your new code into your local `master` branch. Doing it this way, rather than merging your new branch into your local `master` directly, will save you a lot of headaches later. Trust me on this.
