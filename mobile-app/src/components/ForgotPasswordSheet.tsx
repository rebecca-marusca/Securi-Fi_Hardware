import { forwardRef, useState, useCallback, useMemo } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import BottomSheet, { BottomSheetBackdrop, BottomSheetView } from '@gorhom/bottom-sheet';
import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/theme/colors';

type ForgotPasswordSheetProps = {
    onClose: () => void;
};

export const ForgotPasswordSheet = forwardRef<BottomSheet, ForgotPasswordSheetProps>(
    ({ onClose }, ref) => {
        const [email, setEmail] = useState('');
        const [isSubmitting, setIsSubmitting] = useState(false);
        const { resetPassword } = useAuth();

        const snapPoints = useMemo(() => ['45%'], []);

        const handleSendResetLink = async () => {
            if (!email) {
                Alert.alert('Missing email', 'Please enter your email address');
                return;
            }

            setIsSubmitting(true);
            try {
                await resetPassword(email);
                Alert.alert('Check your inbox', 'A password reset link has been sent to your email.');
                setEmail('');
                onClose();
            } catch (error: any) {
                const message = getFirebaseErrorMessage(error.code);
                Alert.alert('Reset failed', message);
            } finally {
                setIsSubmitting(false);
            }
        };

        const renderBackdrop = useCallback(
            (props: any) => (
                <BottomSheetBackdrop
                    {...props}
                    disappearsOnIndex={-1}
                    appearsOnIndex={0}
                    opacity={0.5}
                />
            ),
            []
        );

        return (
            <BottomSheet
                ref={ref}
                index={-1}
                snapPoints={snapPoints}
                enablePanDownToClose
                backdropComponent={renderBackdrop}
                backgroundStyle={styles.sheetBackground}
                handleIndicatorStyle={styles.handleIndicator}
            >
                <BottomSheetView style={styles.content}>
                    <View style={styles.header}>
                        <Text style={styles.headerText}>Reset Password</Text>
                    </View>

                    <Text style={styles.description}>
                        Enter the email address associated with your account, and we'll email you a link to reset your password
                    </Text>

                    <TextInput 
                        style={styles.input}
                        value={email}
                        onChangeText={setEmail}
                        autoCapitalize='none'
                        keyboardType='email-address'
                        autoComplete='email'
                    />

                    <TouchableOpacity
                        style={styles.sendButton}
                        onPress={handleSendResetLink}
                        disabled={isSubmitting}
                    >
                        <Text style={styles.sendButtonText}>
                            {isSubmitting ? 'Sending...' : 'Send reset link'}
                        </Text>
                    </TouchableOpacity>
                </BottomSheetView>
            </BottomSheet>
        )
    }
)

function getFirebaseErrorMessage(code: string): string {
  switch (code) {
    case 'auth/invalid-email':
      return 'That email address looks invalid.';
    case 'auth/user-not-found':
      return 'No account found with that email.';
    default:
      return 'Something went wrong. Please try again.';
  }
}

const styles = StyleSheet.create({
  sheetBackground: {
    backgroundColor: colors.darkGreen,
  },
  handleIndicator: {
    backgroundColor: colors.lightGreen
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
  },
  header: {
    backgroundColor: colors.darkGreen,
    // borderColor: colors.shadowGrey,
    // borderWidth: 1,
    marginHorizontal: -20,
    paddingVertical: 16,
  },
  headerText: {
    color: colors.lightGreen,
    fontFamily: 'Urbanist-Bold',
    fontSize: 20,
    textAlign: 'center',
  },
  description: {
    fontFamily: 'Urbanist-SemiBold',
    textAlign: 'center',
    color: colors.lightGreen,
    fontSize: 13,
    marginBottom: 16,
    lineHeight: 18,
  },
  input: {
    backgroundColor: colors.white,
    borderWidth: 2.5,
    borderColor: colors.shadowGrey,
    borderRadius: 8,
    padding: 12,
    fontFamily: 'Urbanist-Regular',
    fontSize: 16,
    marginBottom: 20,
  },
  sendButton: {
    backgroundColor: colors.shadowGrey,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  sendButtonText: {
    color: colors.lightGreen,
    fontFamily: 'Urbanist-Bold',
    fontSize: 15,
  },
});