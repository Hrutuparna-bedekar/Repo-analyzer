/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import { Platform } from 'react-native';

const tintColorLight = '#0a7ea4';
const tintColorDark = '#fff';

export const Colors = {
  light: {
    text: '#11181C',
    background: '#fff',
    tint: tintColorLight,
    icon: '#687076',
    tabIconDefault: '#687076',
    tabIconSelected: tintColorLight,
    primary: '#0a7ea4',
    secondary: '#bf5af2',
    accent: '#00e5ff',
  },
  dark: {
    text: '#f0f6fc',
    background: '#05070f',
    tint: '#00e5ff',
    icon: '#aeb6bf',
    tabIconDefault: '#70818f',
    tabIconSelected: '#00e5ff',
    primary: '#4d94ff',
    secondary: '#bf5af2',
    accent: '#00e5ff',
    surface: '#0d1117',
    card: '#161b22',
    cardHover: '#1c2333',
    border: '#21262d',
    textDim: '#aeb6bf',
    textMuted: '#70818f',
    cyan: '#00e5ff',
    purple: '#bf5af2',
    orange: '#ff9f0a',
    red: '#ff453a',
    blue: '#4d94ff',
    green: '#30d158',
    teal: '#5ac8fa',
    pink: '#ff2d55',
  },
};

export const NodeColors: Record<string, string> = {
  repository: '#ff453a',
  folder: '#ff9f0a',
  file: '#4d94ff',
  class: '#30d158',
  function: '#bf5af2',
  method: '#5ac8fa',
};

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded: "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});
