import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { subscribeToUserProfile, type UserProfile } from '@/services/userProfile';

export function useUserProfile() {
    const { user } = useAuth();
    const [ profile, setProfile ] = useState<UserProfile | null>(null);
    const [ isLoading, setIsLoading ] = useState(true);

    useEffect(() => {
        if(!user) {
            setProfile(null);
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        const unsubscribe = subscribeToUserProfile(user.uid, (data) => {
            setProfile(data);
            setIsLoading(false);
        });

        return unsubscribe;
    }, [user]);

    return { profile, isLoading };
}