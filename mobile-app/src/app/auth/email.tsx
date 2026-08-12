import { useState, useRef } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, Keyboard, Image, KeyboardAvoidingView, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { getAuth, signInWithEmailAndPassword, fetchSignInMethodsForEmail } from '@react-native-firebase/auth';
import { colors } from '@/theme/colors';
import { ForgotPasswordSheet } from "@/components/ForgotPasswordSheet";
import BottomSheet from "@gorhom/bottom-sheet"

// Codes that mean "no account exists with this email" — newer SDK
// versions return invalid-credential instead of user-not-found so they
// don't leak which emails have accounts.
const NO_ACCOUNT_CODES = new Set(['auth/user-not-found', 'auth/invalid-credential']);

export default function EmailScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordRevealed, setPasswordRevealed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sheetVisible, setSheetVisible] = useState(false);
  const passwordInputRef = useRef<TextInput>(null);
  const forgotPasswordSheetRef = useRef<BottomSheet>(null);

  const handleEmailContinue = async () => {
    if (!email.trim()) {
      setError('Enter your email to continue');
      return;
    }
    
    setError(null);
    setIsSubmitting(true);
    Keyboard.dismiss();

    try {
      // Check if any sign-in methods exist for this email
      const methods = await fetchSignInMethodsForEmail(getAuth(), email.trim());
      
      if (methods.length === 0) {
        // No account exists, go to sign up
        router.push({ pathname: '/auth/signup', params: { email: email.trim() } });
      } else {
        // Account exists, reveal password input
        setPasswordRevealed(true);
        setTimeout(() => passwordInputRef.current?.focus(), 50);
      }
    } catch (err: any) {
      console.log('Firebase fetch methods error:', err?.code);
      setError('Something went wrong checking your email.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePasswordContinue = async () => {
    if (!password) {
      setError('Enter your password to continue');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    Keyboard.dismiss();

    try {
      await signInWithEmailAndPassword(getAuth(), email.trim(), password);
      // Success: onAuthStateChanged in root layout handles the redirect.
    } catch (error: any) {
      const code = error?.code as string | undefined;

      if (code && NO_ACCOUNT_CODES.has(code)) {
        router.push({ pathname: '/auth/signup', params: { email: email.trim() } });
        return;
      }

      if (code === 'auth/wrong-password') {
        setError('Incorrect password');
        return;
      }

      setError('Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
	<KeyboardAvoidingView
		style={styles.container}
		behavior={Platform.OS === "ios" ? "padding" : undefined}
	>
		<ScrollView 
			contentContainerStyle={styles.scrollContent}
			keyboardShouldPersistTaps="handled"
		>
		<Image
			source={require('@/assets/images/log-in-text.png')}
			style={styles.headerImage}
			resizeMode="contain"
		/>

		<Text style={styles.label}>Enter your email</Text>
		<TextInput
			style={[styles.input, passwordRevealed && styles.inputMuted]}
			value={email}
			onChangeText={setEmail}
			editable={!passwordRevealed}
			autoCapitalize="none"
			keyboardType="email-address"
			autoComplete="email"
			placeholderTextColor={colors.textMuted}
		/>

		{passwordRevealed && (
			<>
			<Text style={[styles.label, styles.passwordLabel]}>Password</Text>
			<TextInput
				ref={passwordInputRef}
				style={styles.input}
				value={password}
				onChangeText={setPassword}
				secureTextEntry
				autoComplete="password"
				placeholderTextColor={colors.textMuted}
			/>
			<Pressable onPress={() => forgotPasswordSheetRef.current?.expand()}>
				<Text style={styles.forgotLink}>Forgot password?</Text>
			</Pressable>
			</>
		)}

		{error && <Text style={styles.errorText}>{error}</Text>}
		<View style={styles.spacer} />

		<Pressable
			style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
			onPress={passwordRevealed ? handlePasswordContinue : handleEmailContinue}
			disabled={isSubmitting}
		>
			<Text style={styles.buttonText}>{isSubmitting ? 'Please wait…' : 'Continue'}</Text>
		</Pressable>

		<ForgotPasswordSheet
			ref={forgotPasswordSheetRef}
			onClose={() => setSheetVisible(false)}
			initialEmail={email.trim()}
		/>
		</ScrollView>
	</KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.base,
    paddingHorizontal: 24,
    paddingTop: 80,
	paddingBottom: 40
  },
  scrollContent: {
	paddingTop: 0,
	paddingBottom: 40,
	flexGrow: 1
  },
  headerImage: {
    width: 500,
    height: 150,
    alignSelf: 'center',
  },
  spacer: {
    flex: 1,
  },
  label: {
    fontFamily: 'SF-Pro-Text-Bold',
    fontSize: 17,
    color: colors.text,
    marginBottom: 8,
  },

  passwordLabel: {
    marginTop: 20,
  },
  input: {
    backgroundColor: colors.bgSecondary2,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 15,
    fontFamily: 'SF-Pro-Text-Medium',
    fontSize: 15,
    color: colors.textMuted,
	borderColor: colors.accent,
	borderWidth: 2
  },
  inputMuted: {
    color: colors.textMuted,
  },
  forgotLink: {
	alignSelf: 'center',
    fontFamily: 'SF-Pro-Text-Semibold',
    fontSize: 13,
    color: colors.textMuted,
    textDecorationLine: 'underline',
    marginTop: 15,
  },

  errorText: {
    fontFamily: 'SF-Pro-Text-Regular',
    fontSize: 13,
    color: '#B3453D',
    marginTop: 12,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: 'center',
	marginHorizontal: 15,
  },

  buttonPressed: {
    opacity: 0.85,
  },

  buttonText: {
    fontFamily: 'SF-Pro-Text-Semibold',
    fontSize: 16,
    color: colors.base,
  },
});