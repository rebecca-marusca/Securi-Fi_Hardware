import { View, Text } from 'react-native';
import {colors} from '@/theme/colors';

export default function HomeScreen() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.lightGreen }}>
      <Text>Home — coming soon</Text>
    </View>
  );
}