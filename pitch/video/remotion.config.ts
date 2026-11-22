import { Config } from "@remotion/cli/config";

// Use the installed Chrome instead of downloading a headless shell.
Config.setBrowserExecutable("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");
Config.setVideoImageFormat("jpeg");
Config.setConcurrency(4);
