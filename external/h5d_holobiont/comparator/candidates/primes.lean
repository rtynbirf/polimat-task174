import Mathlib.Data.Nat.Prime.Infinite

def IsPrime (n : Nat) := 1 < n ∧ ∀ k, 1 < k → k < n → ¬ k ∣ n

theorem InfinitudeOfPrimes : ∀ n, ∃ p > n, IsPrime p := by
  intro n
  have h := Nat.exists_infinite_primes (n + 1)
  match h with
  | ⟨p, hle, hpr⟩ =>
    refine ⟨p, ?_, Nat.Prime.one_lt hpr, ?_⟩
    · omega
    · intro k hk1 hk2 hdvd
      cases Nat.Prime.eq_one_or_self_of_dvd hpr k hdvd with
      | inl h0 => omega
      | inr h0 => omega
