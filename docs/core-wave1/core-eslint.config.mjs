import globals from '../../service-desk-app/node_modules/globals/index.js';
import hooks from '../../service-desk-app/node_modules/eslint-plugin-react-hooks/index.js';
export default [{linterOptions:{reportUnusedDisableDirectives:'off'},plugins:{'react-hooks':hooks},files:['**/*.{js,jsx}'],languageOptions:{ecmaVersion:'latest',sourceType:'module',parserOptions:{ecmaFeatures:{jsx:true}},globals:{...globals.browser,...globals.node}},rules:{'no-undef':'error','no-unreachable':'error','no-dupe-args':'error','no-dupe-keys':'error','valid-typeof':'error'}}];
