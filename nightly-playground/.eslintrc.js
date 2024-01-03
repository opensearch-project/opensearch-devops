module.exports = {
    env: {
        browser: false,
        es6: true,
        jest: true,
    },
    extends: [
        'airbnb-base',
    ],
    globals: {
        Atomics: 'readonly',
        SharedArrayBuffer: 'readonly',
    },
    parser: '@typescript-eslint/parser',
    parserOptions: {
        ecmaVersion: 2018,
    },
    plugins: [
        '@typescript-eslint',
    ],
    rules: {
        hasTrailingComma: 'off',
        indent: ['error', 2],
        'import/extensions': 'error',
        'import/no-namespace': 'error',
        'import/no-unresolved': 'error',
        'import/no-extraneous-dependencies': 'error',
        'import/prefer-default-export': 'off',
        'max-classes-per-file': 'off',
        'no-unused-vars': 'off',
        'no-new': 'off',
        'max-len': ['error', { 'code': 160, 'ignoreComments': true }],
        "no-param-reassign": 0,
        "no-shadow": "off",
        "@typescript-eslint/no-shadow": ["error"]
    },
};