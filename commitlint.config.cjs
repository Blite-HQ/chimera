module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore', 'ci', 'build', 'revert']
    ],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'header-max-length': [2, 'always', 100]
  },
  // Dependabot's auto-generated body (changelog links, one per updated
  // dependency) routinely exceeds body-max-line-length — content we don't
  // control and can't reformat. Its header already follows convention
  // ("chore(deps): ..."), so skip linting the rest of the message.
  ignores: [commit => /Signed-off-by: dependabot\[bot\]/.test(commit)]
};
