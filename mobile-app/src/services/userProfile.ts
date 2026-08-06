import {
    getFirestore,
    doc,
    getDoc,
    setDoc,
    onSnapshot,
    serverTimestamp,
} from '@react-native-firebase/firestore';

export type UserProfile = {
    email: string;
    phoneNumber: string;
    displayName?: string;
    createdAt?: any; // Firestore Timestamp
};

export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  const snapshot = await getDoc(doc(getFirestore(), 'users', uid));
  return snapshot.exists() ? (snapshot.data() as UserProfile) : null;
}

export async function updateUserProfile(
  uid: string,
  data: Partial<UserProfile>
): Promise<void> {
  await setDoc(doc(getFirestore(), 'users', uid), data, { merge: true });
}

export function subscribeToUserProfile(
    uid: string,
    onChange: (profile: UserProfile | null) => void
): () => void {
    return onSnapshot(doc(getFirestore(), 'users', uid), (snapshot) => {
        onChange(snapshot.exists() ? (snapshot.data() as UserProfile) : null);
    });
}