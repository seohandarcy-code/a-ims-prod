// ESLint 9+ flat config.
// 최소 구성: eslint-plugin-vue의 recommended 계열 + typescript-eslint의 recommended 계열.
// 과도하게 엄격한 커스텀 룰은 추가하지 않는다(운영 원칙: PDEP Jenkins lint 단계 통과가 목표).
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
)
