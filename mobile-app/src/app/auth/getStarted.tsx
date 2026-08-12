import { View, Text, Image, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { colors } from '@/theme/colors';

export default function GetStartedScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.illustrationWrap}>
        <Image
          source={require('@/assets/images/securi-fi-logo.png')}
          style={styles.illustration}
          resizeMode="contain"
        />
      </View>

      <Pressable
        style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
        onPress={() => router.push("/auth/email")}
      >
        <Text style={styles.buttonText}>Get started</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.base,
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingTop: 64,
    paddingBottom: 48,
  },
  illustrationWrap: {
     flex: 1, 
     alignItems: 'center', 
     justifyContent: 'center' 
  },
  illustration: { 
    width: 600, 
    height: 550
  },
  button: { 
    backgroundColor: colors.accent,
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: 'center',
	  marginHorizontal: 15,
    marginBottom: 50
  },
  buttonPressed: { 
    opacity: 0.85 
  },
  buttonText: { 
    fontSize: 17, 
    color: colors.base,
    fontFamily: 'SF-Pro-Text-Medium'
  },
});