import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Image,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/theme/colors';

export default function SignupScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { signUp } = useAuth();
  const router = useRouter();

  const handleSignup = async () => {
    if (!email || !password || !confirmPassword || !phoneNumber) {
      Alert.alert('Missing info', 'Please fill in all fields.');
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert('Password mismatch', 'Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      Alert.alert('Weak password', 'Password must be at least 6 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      await signUp(email, password);
      // TODO: once signed up, save phoneNumber to Firestore under the new user's UID
      // (auth() alone doesn't store phone number — that needs a separate DB write)

      // No manual navigation needed — root _layout.tsx will
      // detect the auth state change and redirect automatically.
    } catch (error: any) {
      const message = getFirebaseErrorMessage(error.code);
      Alert.alert('Signup failed', message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <Image
          source={require('@/assets/images/securi-fi-text-dark.png')}
          style={styles.logo}
          resizeMode="contain"
        />

        <Text style={styles.label}>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
        />

        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="new-password"
        />

        <Text style={styles.label}>Confirm password</Text>
        <TextInput
          style={styles.input}
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry
          autoComplete="new-password"
        />

        <Text style={styles.label}>Phone Number</Text>
        <TextInput
          style={styles.input}
          value={phoneNumber}
          onChangeText={setPhoneNumber}
          keyboardType="phone-pad"
          autoComplete="tel"
        />

        <TouchableOpacity
          style={styles.signupButton}
          onPress={handleSignup}
          disabled={isSubmitting}
        >
          <Text style={styles.signupButtonText}>
            {isSubmitting ? 'Signing up...' : 'Sign up'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.loginLink}
          onPress={() => router.push('/auth/login')}
        >
          <Text style={styles.loginText}>
            Already have an account? <Text style={styles.link}>Log in</Text>
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function getFirebaseErrorMessage(code: string): string {
  switch (code) {
    case 'auth/email-already-in-use':
      return 'An account with this email already exists.';
    case 'auth/invalid-email':
      return 'That email address looks invalid.';
    case 'auth/weak-password':
      return 'Password is too weak — please use at least 6 characters.';
    default:
      return 'Something went wrong. Please try again.';
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.lightGreen,
    paddingHorizontal: 24,
    paddingTop: 60
  },
  scrollContent: {
    paddingTop: 0,
    paddingBottom: 40,
    flexGrow: 1,
  },
  logo: {
    width: 423,
    height: 150,
    alignSelf: 'center'
  },
  label: {
    fontFamily: 'Urbanist-Bold',
    color: colors.blue,
    marginBottom: 6,
    marginTop: 16,
  },
  input: {
    backgroundColor: colors.lightBlue,
    borderWidth: 2.5,
    borderColor: colors.blue,
    borderRadius: 8,
    padding: 12,
    fontFamily: 'Urbanist-Regular',
    fontSize: 16,
  },
  signupButton: {
    backgroundColor: colors.blue,
    borderRadius: 30,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 32,
    width: 120,
    alignSelf: 'center'
  },
  signupButtonText: {
    color: colors.white,
    fontFamily: 'Urbanist-Bold',
    fontSize: 16
  },
  link: {
    color: colors.blue,
    fontFamily: 'Urbanist-Bold',
    textAlign: 'center',
    marginTop: 20,
  },
  loginLink: {
    marginTop: 'auto',
    marginBottom: 40
  },
  loginText: {
    textAlign: 'center',
    fontFamily: 'Urbanist-SemiBold',
    color: colors.shadowGrey,
  },
});