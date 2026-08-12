import { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, Image, KeyboardAvoidingView, ScrollView, Platform } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { getAuth, createUserWithEmailAndPassword, updateProfile } from '@react-native-firebase/auth';
import { getFirestore, doc, setDoc, serverTimestamp } from '@react-native-firebase/firestore';
import { colors } from '@/theme/colors';

export default function SignupScreen() {
  const { email } = useLocalSearchParams<{ email: string }>();

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleContinue = async () => {
    if (!name.trim() || !phone.trim() || !password || !confirmPassword) {
      setError('Fill in all fields to continue');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords don\u2019t match');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const auth = getAuth();
      const credential = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(credential.user, { displayName: name.trim() });

      await setDoc(
        doc(getFirestore(), 'users', credential.user.uid),
        { email, phoneNumber: phone.trim(), displayName: name.trim(), createdAt: serverTimestamp() },
        { merge: true }
      );
      // Success: onAuthStateChanged in root layout handles the redirect.
    } catch (error: any) {
      const code = error?.code as string | undefined;

      if (code === 'auth/email-already-in-use') {
        setError('An account with this email already exists');
      } else if (code === 'auth/weak-password') {
        setError('Password is too weak');
      } else {
        setError('Something went wrong. Please try again.');
      }
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
        source={require('@/assets/images/sign-up-text.png')}
        style={styles.headerImage}
        resizeMode="contain"
      />

        <Text style={styles.label}>Name</Text>
        <TextInput style={styles.input} value={name} onChangeText={setName} placeholderTextColor={colors.textMuted} />

        <Text style={styles.label}>Phone Number</Text>
        <TextInput style={styles.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholderTextColor={colors.textMuted} />

        <Text style={styles.label}>Password</Text>
        <TextInput style={styles.input} value={password} onChangeText={setPassword} secureTextEntry placeholderTextColor={colors.textMuted} />

        <Text style={styles.label}>Confirm Password</Text>
        <TextInput style={styles.input} value={confirmPassword} onChangeText={setConfirmPassword} secureTextEntry placeholderTextColor={colors.textMuted} />

        {error && <Text style={styles.errorText}>{error}</Text>}
        <View style={styles.spacer} />

        <Pressable style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]} onPress={handleContinue} disabled={isSubmitting}>
          <Text style={styles.buttonText}>{isSubmitting ? 'Creating account…' : 'Continue'}</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.base,
    paddingHorizontal: 24,
    paddingTop: 64,
    paddingBottom: 40
  },
  scrollContent: {
	paddingBottom: 40,
	flexGrow: 1
  },
  headerImage: {
    width: 500,
    height: 150,
    alignSelf: 'center',
  },
  label: {
    fontFamily: 'SF-Pro-Text-Bold',
    fontSize: 17,
    color: colors.text,
    marginTop: 16,
    marginBottom: 8,
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
  errorText: {
    fontFamily: 'SF-Pro-Text-Regular',
    fontSize: 13,
    color: '#B3453D',
    marginTop: 12,
  },
  spacer: {
    flex: 1,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 30,
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