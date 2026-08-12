import { forwardRef, useState, useCallback, useMemo, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import BottomSheet, { BottomSheetBackdrop, BottomSheetView } from '@gorhom/bottom-sheet';
import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/theme/colors';

type ForgotPasswordSheetProps = {
    onClose: () => void;
    initialEmail?: string;
};

export const ForgotPasswordSheet = forwardRef<BottomSheet, ForgotPasswordSheetProps>(
    ({ onClose, initialEmail = '' }, ref) => {
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

        useEffect(() => {
            setEmail(initialEmail);
        }, [initialEmail]);

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
                        We'll send a link to the email address you signed up with.
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
                            {isSubmitting ? 'Sending...' : 'Send link'}
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
    backgroundColor: colors.bgSecondary1,
  },
  handleIndicator: {
    backgroundColor: colors.accent
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
  },
  header: {
    backgroundColor: colors.bgSecondary1,
    marginHorizontal: -20,
    paddingVertical: 16,
  },
  headerText: {
    color: colors.textMuted,
    fontFamily: 'SF-Pro-Text-Semibold',
    fontSize: 17,
    textAlign: 'center',
  },
  description: {
    fontFamily: 'SF-Pro-Text-Regular',
    textAlign: 'center',
    color: colors.text,
    fontSize: 13,
    marginBottom: 15,
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
	borderWidth: 2,
    marginBottom: 15
  },
  sendButton: {
    backgroundColor: colors.accent,
    borderRadius: 1000,
    paddingVertical: 15,
    width: 118,
    alignItems: 'center',
    alignSelf: 'center'
  },
  sendButtonText: {
    color: colors.bgSecondary1,
    fontFamily: 'SF-Pro-Text-Semibold',
    fontSize: 15,
  },
});