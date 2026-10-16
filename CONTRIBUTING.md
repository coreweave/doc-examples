<!--
SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
SPDX-License-Identifier: MIT
-->

# Contributing

This repository contains examples and supporting materials for CoreWeave
documentation. Public feedback, bug reports, and suggestions are welcome through
GitHub issues. Pull requests are currently limited to repository collaborators.

## Report an issue or propose a change

Use [GitHub issues](https://github.com/coreweave/doc-examples/issues) to report a
problem or discuss a proposed example. Include the relevant file, expected
behavior, actual behavior, and steps to reproduce the problem. Discuss large
changes with the maintainers before starting work.

Remove credentials, customer data, and confidential information from reports,
logs, examples, and commits.

## Contributor license agreement

Contributors must agree to the [CoreWeave CLA](./CLA.md) when pushing code to this
project. The CLA also covers documentation and other copyrightable material
submitted to the project.

Agreement with the CoreWeave CLA must be signified by including a `Signed-off-by`
trailer in every submitted Git commit to this repository. By signing off, you
certify that you have the right to submit the contribution and that you agree to
and are bound by the CoreWeave Contributor License Agreement in effect at the date
of your submission, found in [CLA.md](./CLA.md), which governs your submission. If
you are contributing on behalf of an entity, you further certify that you are
authorized to bind that entity to the CLA.

Use your name and email address in your Git author identity. Add a sign-off to
each commit with:

```bash
git commit --signoff -m "Describe your change"
```

This adds a `Signed-off-by: Your Name <your-email>` trailer to the commit message.
A sign-off records your agreement to the CLA; it does not require a cryptographic
commit signature. Read the CLA before submitting a contribution.

## Submit a pull request

1. If you are a repository collaborator, create a branch for your change.
   Otherwise, open an issue describing your proposed change.
2. Keep the change focused and follow the conventions of the example you are
   updating. Update its supporting documentation when behavior or usage changes.
3. Run the relevant tests or validate the example in an appropriate environment.
   Describe the validation you performed and any limitations in the pull request.
4. Sign off every commit and open a pull request against `main`. Explain the
   problem, the proposed change, and any related GitHub issues.
5. Respond to maintainer feedback and sign off any additional commits.

For a missing sign-off on your latest commit, review the CLA and then run
`git commit --amend --no-edit --signoff`. If earlier commits need sign-offs, ask a
maintainer for guidance before updating the pull request branch.

## Maintainer review

The maintainers identified in [CODEOWNERS](./CODEOWNERS) review contributions for
scope, correctness, documentation, validation, and suitability for publication.
Maintainers may request changes or decline a contribution.

Before merging an external contribution, maintainers must verify that every
submitted commit has the contributor's `Signed-off-by` trailer. If any sign-off
is missing, request it from the contributor and wait for the corrected commits
before merging. Do not add a sign-off on someone else's behalf.

## Licensing and third-party materials

CoreWeave's original contributions are licensed under the [MIT License](./LICENSE).
This repository may include or reference third-party software, models, images, or
other materials, which remain subject to their respective license terms. Nothing
in this repository changes those terms or grants rights beyond those CoreWeave is
authorized to grant.

Contributions must be submitted under terms that permit their inclusion and
distribution in this repository and are subject to the
[CoreWeave CLA](./CLA.md). If your contribution includes third-party material,
identify its source and applicable license and preserve any required copyright
notices and attribution.
