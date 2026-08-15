import { Image } from "expo-image";
import * as SplashScreen from "expo-splash-screen";
import { useState } from "react";
import { StyleSheet, View } from "react-native";
import Animated, { Easing, Keyframe } from "react-native-reanimated";
import { scheduleOnRN } from "react-native-worklets";

const DURATION = 6000;

const splashKeyframe = new Keyframe({
  0: { transform: [{ scale: 1 }], opacity: 1 },
  20: { opacity: 1 },
  70: { opacity: 0, easing: Easing.elastic(0.7) },
  100: { opacity: 0, transform: [{ scale: 1 }], easing: Easing.elastic(0.7) },
});

export function SplashOverlay() {
  const [animate, setAnimate] = useState(false);
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  const image = (
    <Image
      style={styles.image}
      source={require("@/assets/images/securi-fi-text-lightGreen.png")}
    />
  );

  return animate ? (
    <Animated.View
      entering={splashKeyframe.duration(DURATION).withCallback((finished) => {
        "worklet";
        if (finished) scheduleOnRN(setVisible, false);
      })}
      style={styles.overlay}
    >
      {image}
    </Animated.View>
  ) : (
    <View
      onLayout={() => {
        SplashScreen.hideAsync().finally(() => setAnimate(true));
      }}
      style={styles.overlay}
    >
      {image}
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "#557473",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  image: {
    width: 390,
    height: 390,
  },
});
