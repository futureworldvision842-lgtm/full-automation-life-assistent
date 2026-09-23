import type { Actor } from './types';

export type LocalAccountInput = Pick<Actor, 'name' | 'email' | 'city' | 'country' | 'skills' | 'interests'>;

export function createLocalDemoActor(input: LocalAccountInput, id = `u-local-${Date.now()}`): Actor {
  const name = input.name.trim();
  const email = input.email.trim().toLowerCase();
  if (!name) throw new Error('Add a name before creating an account.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('Add a valid email address.');
  return {
    id, name, email, city: input.city.trim() || 'Islamabad', country: input.country.trim() || 'Pakistan', roles: ['member'],
    skills: input.skills.filter(Boolean), interests: input.interests.filter(Boolean), impactPoints: 0,
    avatar: name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase(), privacy: 'community'
  };
}
