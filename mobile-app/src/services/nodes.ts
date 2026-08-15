import {
    collection,
    doc,
    getFirestore,
    onSnapshot,
    query,
    updateDoc,
    where,
} from "@react-native-firebase/firestore";

export type Node = {
  id: string;
  name: string;
  room: string;
  status: "online" | "offline";
};

export function subscribeToUserNodes(
  uid: string,
  onChange: (nodes: Node[]) => void,
): () => void {
  const q = query(
    collection(getFirestore(), "nodes"),
    where("ownerId", "==", uid),
  );
  return onSnapshot(
    q,
    (snapshot) => {
      if (!snapshot) {
        onChange([]);
        return;
      }

      const nodes = snapshot.docs.map(
        (d) => ({ id: d.id, ...d.data() }) as Node,
      );
      onChange(nodes);
    },
    (error) => {
      console.error("Firestore nodes listener error:", error);
      onChange([]);
    },
  );
}

export async function renameNode(
  nodeId: string,
  newName: string,
): Promise<void> {
  await updateDoc(doc(getFirestore(), "nodes", nodeId), { name: newName });
}
