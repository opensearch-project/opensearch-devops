module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/test'],
  preset: 'ts-jest',
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest',
  },
  testTimeout: 50000,
};
