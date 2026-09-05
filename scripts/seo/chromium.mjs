// Общий выбор Chromium для скриптов, рисующих и проверяющих письмо.
import { existsSync } from 'node:fs';

// Исполняемый файл Chromium ищется в трёх местах по убыванию явности:
// переменная CHROMIUM_EXECUTABLE, предустановленный браузер сессионной среды
// и, наконец, браузер самого Playwright (его ставит `playwright install`).
// Жёсткий путь сессии здесь стоял один — и ронял ежедневный конвейер в
// Actions, где такого файла нет (04.09.2026: письмо не собралось).
const SESSION_CHROMIUM = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
export function chromiumExecutable() {
  const explicit = process.env.CHROMIUM_EXECUTABLE;
  if (explicit) return explicit;
  return existsSync(SESSION_CHROMIUM) ? SESSION_CHROMIUM : undefined;
}
