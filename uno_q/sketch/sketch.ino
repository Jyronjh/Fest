// App Lab MCU. The RPC callback never waits for scrolling to finish.
#include <Arduino_RouterBridge.h>
#include <ArduinoGraphics.h>
#include <Arduino_LED_Matrix.h>
#include <atomic>

std::atomic<bool> requested(false);

void welcome() { requested.store(true); }

void show_text(String text) {
  // All display-specific code lives here. Empty text clears the display.
  // Replace only this function to use an I2C LCD instead.
  static Arduino_LED_Matrix matrix;
  static bool initialized = false;
  static unsigned long lastFrame = 0;
  static int x = 13;
  if (!initialized) { matrix.begin(); initialized = true; }
  if (text.length() == 0) { matrix.clear(); x = 13; return; }
  if (millis() - lastFrame < 45) return;
  lastFrame = millis();
  matrix.beginDraw();
  matrix.background(0, 0, 0);
  matrix.stroke(255, 255, 255);
  matrix.textFont(Font_4x6);
  matrix.beginText(x, 1, 255, 255, 255);
  matrix.print(text);
  matrix.endText();
  matrix.endDraw();
  if (--x < -(int)text.length() * 4) x = 13;
}

void setup() {
  show_text("");
  Bridge.begin();
  Bridge.provide("welcome", welcome);
}

void loop() {
  static bool active = false;
  static unsigned long started = 0;
  if (requested.exchange(false)) {
    show_text("");
    started = millis();
    active = true;
  }
  if (active && millis() - started >= 10000) {
    show_text("");
    active = false;
  }
  if (active) show_text("YOU ARE WELCOME - PICK A SOUVENIR");
  delay(5);
}
