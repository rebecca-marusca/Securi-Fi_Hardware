import { useState, useRef } from 'react';
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
} from 'react-native';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { colors } from '@/theme/colors';
import BottomSheet from '@gorhom/bottom-sheet';
import { ForgotPasswordSheet } from '@/components/ForgotPasswordSheet';

export default function LoginScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { signIn } = useAuth();
    const router = useRouter();
    const bottomSheetRef = useRef<BottomSheet>(null);

    const handleLogin = async () => {
        if(!email || !password) {
            Alert.alert('Missing info', 'Please enter both email and password.')
            return;
        }

        setIsSubmitting(true);
        try {
            await signIn(email, password) // no manual navigation, detecteaza autentificarea si redirectioneaza direct
        } catch (error: any) {
            const message = getFirebaseErrorMessage(error.code);
            Alert.alert('Login failed', message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const openForgotPassword = () => {
      console.log('Forgot password pressed')
      bottomSheetRef.current?.expand();
    };

    const closeForgotPassword = () => {
      bottomSheetRef.current?.close();
    };

    return (
      <>
        <KeyboardAvoidingView  style = {styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <Image
                source = {require('../../../assets/images/securi-fi-text-dark.png')}
                style={styles.logo}
                resizeMode="contain"
            />

            <Text style={styles.label}>Email</Text>
            <TextInput
                style = {styles.input}
                value = {email}
                onChangeText = {setEmail}
                autoCapitalize='none'
                keyboardType = 'email-address'
                autoComplete = 'email'
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
                style = {styles.input}
                value = {password}
                onChangeText = {setPassword}
                autoCapitalize='none'
            />

            <TouchableOpacity
                style = {styles.loginButton}
                onPress = {handleLogin}
                disabled = {isSubmitting}
            >
                <Text style = {styles.loginButtonText}>
                    {isSubmitting ? 'Logging in...' : 'Log in'}
                </Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={openForgotPassword}>
                <Text style={styles.link}>Forgot Password? </Text>
            </TouchableOpacity>

            <TouchableOpacity
                style = {styles.signupLink}
                onPress={() => router.push('/auth/signup')}
            >
                <Text style={styles.signupText}>
                    Don't have an account? <Text style={styles.link}>Sign Up</Text>
                </Text>
            </TouchableOpacity>

        </KeyboardAvoidingView>

        <ForgotPasswordSheet ref={bottomSheetRef} onClose={closeForgotPassword} />
      </>
    )
}

function getFirebaseErrorMessage(code: string): string {
  switch (code) {
    case 'auth/invalid-email':
      return 'Email address is invalid.';
    case 'auth/user-not-found':
      return 'No account found with that email.';
    case 'auth/wrong-password':
    case 'auth/invalid-credential':
      return 'Incorrect email or password.';
    case 'auth/too-many-requests':
      return 'Too many attempts. Please try again later.';
    default:
      return 'Something went wrong. Please try again.';
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.lightGreen,
    paddingHorizontal: 24,
    paddingTop: 60,
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
  loginButton: {
    backgroundColor: colors.blue,
    borderRadius: 30,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 32,
    width: 120,
    alignSelf: 'center'
  },
  loginButtonText: {
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
  signupLink: {
    marginTop: 'auto',
    marginBottom: 40
  },
  signupText: {
    textAlign: 'center',
    fontFamily: 'Urbanist-SemiBold',
    color: colors.shadowGrey,
  },
});