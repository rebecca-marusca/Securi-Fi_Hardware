import {
  doc,
  getDoc,
  getFirestore,
  onSnapshot,
  setDoc,
} from "@react-native-firebase/firestore";

export type NotificationPrefs = {
  breakIns: boolean;
  fires: boolean;
  gasLeaks: boolean;
  nodeStatus: boolean;
  lowBattery: boolean;
  firmwareUpdates: boolean;
  security: boolean;
  productUpdates: boolean;
};

export const defaultNotificationPrefs: NotificationPrefs = {
  breakIns: true,
  fires: true,
  gasLeaks: true,
  nodeStatus: true,
  lowBattery: false,
  firmwareUpdates: false,
  security: true,
  productUpdates: false,
};

export type UserProfile = {
  email: string;
  phoneNumber: string;
  displayName?: string;
  createdAt?: any; // Firestore Timestamp
  photoURL?: string;
  notificationPrefs?: NotificationPrefs;
};

export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  const snapshot = await getDoc(doc(getFirestore(), "users", uid));
  return snapshot.exists() ? (snapshot.data() as UserProfile) : null;
}

export async function updateUserProfile(
  uid: string,
  data: Partial<UserProfile>,
): Promise<void> {
  await setDoc(doc(getFirestore(), "users", uid), data, { merge: true });
}

export function subscribeToUserProfile(
  uid: string,
  onChange: (profile: UserProfile | null) => void,
): () => void {
  return onSnapshot(
    doc(getFirestore(), "users", uid),
    (snapshot) => {
      if (!snapshot) {
        onChange(null);
        return;
      }

      onChange(snapshot.exists() ? (snapshot.data() as UserProfile) : null);
    },
    (error) => {
      console.error("Firestore listener error:", error);
    },
  );
}
