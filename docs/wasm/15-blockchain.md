# Capítulo 15: Wasm e Blockchain

## Introdução

O WebAssembly está revolucionando o desenvolvimento de smart contracts e blockchain ao oferecer uma alternativa segura e performática às EVM (Ethereum Virtual Machine) tradicionais. Plataformas como Polkadot, NEAR Protocol e Cosmos já adotaram WASM como base para seus sistemas de smart contracts, aproveitando sua portabilidade, segurança e eficiência.

Diferente da EVM, que é uma máquina virtual customizada para Ethereum, WASM é um padrão aberto e portável que pode ser executado em múltiplas plataformas. Isso permite que desenvolvedores usem linguagens como Rust, C++ e Go para escrever smart contracts, em vez de Solidity ou Vyper.

O modelo de segurança do WASM também é mais robusto que o da EVM, com sandboxing nativo, memória isolada e controle granular de capacidades. Isso reduz significativamente a superfície de ataque e torna os smart contracts mais seguros por padrão.

Vamos explorar como diferentes plataformas blockchain implementam WASM para smart contracts, as técnicas de medición de gas, execução determinística e ferramentas de auditoria disponíveis.

---

## 15.1 Smart Contracts in Wasm

### Visão Geral da Arquitetura

Os smart contracts em WebAssembly seguem um modelo similar ao desenvolvimento de aplicações WASM tradicionais, com algumas diferenças importantes relacionadas à execução em blockchain:

1. **Execução Determinística**: O mesmo input deve sempre produzir o mesmo output
2. **Isolamento Total**: Contratos não podem acessar estado externo diretamente
3. **Medição de Recursos**: Cada operação deve ser contabilizada (gas)
4. **Persistência de Estado**: O estado do contrato é armazenado na blockchain

### Estrutura Básica de um Smart Contract

```rust
// basic-contract/src/lib.rs
use borsh::{BorshDeserialize, BorshSerialize};
use serde::{Deserialize, Serialize};

#[derive(BorshDeserialize, BorshSerialize, Serialize, Deserialize)]
pub struct ContractState {
    pub owner: [u8; 32],
    pub balances: std::collections::HashMap<[u8; 32], u128>,
    pub total_supply: u128,
    pub name: String,
    pub symbol: String,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct InitArgs {
    pub name: String,
    pub symbol: String,
    pub initial_supply: u128,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct TransferArgs {
    pub to: [u8; 32],
    pub amount: u128,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct BalanceArgs {
    pub account: [u8; 32],
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct MintArgs {
    pub to: [u8; 32],
    pub amount: u128,
}

pub struct TokenContract {
    state: ContractState,
}

impl TokenContract {
    pub fn new() -> Self {
        Self {
            state: ContractState {
                owner: [0; 32],
                balances: std::collections::HashMap::new(),
                total_supply: 0,
                name: String::new(),
                symbol: String::new(),
            },
        }
    }
    
    pub fn init(&mut self, args: InitArgs) -> Result<(), ContractError> {
        // Only allow initialization once
        if self.state.total_supply > 0 {
            return Err(ContractError::AlreadyInitialized);
        }
        
        // Set owner to caller
        self.state.owner = self.get_caller()?;
        
        // Initialize token
        self.state.name = args.name;
        self.state.symbol = args.symbol;
        self.state.total_supply = args.initial_supply;
        
        // Mint initial supply to owner
        self.state.balances.insert(self.state.owner, args.initial_supply);
        
        // Emit event
        self.emit_event(Event::Initialized {
            owner: self.state.owner,
            name: self.state.name.clone(),
            symbol: self.state.symbol.clone(),
            total_supply: args.initial_supply,
        });
        
        Ok(())
    }
    
    pub fn transfer(&mut self, args: TransferArgs) -> Result<(), ContractError> {
        let caller = self.get_caller()?;
        
        // Check if caller has sufficient balance
        let caller_balance = self.state.balances.get(&caller).copied().unwrap_or(0);
        if caller_balance < args.amount {
            return Err(ContractError::InsufficientBalance {
                available: caller_balance,
                required: args.amount,
            });
        }
        
        // Update balances
        self.state.balances.insert(caller, caller_balance - args.amount);
        
        let to_balance = self.state.balances.get(&args.to).copied().unwrap_or(0);
        self.state.balances.insert(args.to, to_balance + args.amount);
        
        // Emit event
        self.emit_event(Event::Transfer {
            from: caller,
            to: args.to,
            amount: args.amount,
        });
        
        Ok(())
    }
    
    pub fn balance_of(&self, args: BalanceArgs) -> Result<u128, ContractError> {
        Ok(self.state.balances.get(&args.account).copied().unwrap_or(0))
    }
    
    pub fn mint(&mut self, args: MintArgs) -> Result<(), ContractError> {
        let caller = self.get_caller()?;
        
        // Only owner can mint
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        // Update supply and balance
        self.state.total_supply += args.amount;
        let balance = self.state.balances.get(&args.to).copied().unwrap_or(0);
        self.state.balances.insert(args.to, balance + args.amount);
        
        // Emit event
        self.emit_event(Event::Mint {
            to: args.to,
            amount: args.amount,
        });
        
        Ok(())
    }
    
    fn get_caller(&self) -> Result<[u8; 32], ContractError> {
        // In real implementation, this would read from blockchain context
        Ok([0; 32])
    }
    
    fn emit_event(&self, event: Event) {
        // In real implementation, this would log to blockchain
    }
}

#[derive(Debug)]
pub enum ContractError {
    AlreadyInitialized,
    InsufficientBalance { available: u128, required: u128 },
    Unauthorized,
    InvalidArguments,
    StorageError,
}

impl std::fmt::Display for ContractError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::AlreadyInitialized => write!(f, "Contract already initialized"),
            Self::InsufficientBalance { available, required } => {
                write!(f, "Insufficient balance: {} < {}", available, required)
            }
            Self::Unauthorized => write!(f, "Unauthorized"),
            Self::InvalidArguments => write!(f, "Invalid arguments"),
            Self::StorageError => write!(f, "Storage error"),
        }
    }
}

#[derive(Serialize, Deserialize)]
pub enum Event {
    Initialized {
        owner: [u8; 32],
        name: String,
        symbol: String,
        total_supply: u128,
    },
    Transfer {
        from: [u8; 32],
        to: [u8; 32],
        amount: u128,
    },
    Mint {
        to: [u8; 32],
        amount: u128,
    },
}

// WASM entry points
use std::alloc::{alloc, dealloc, Layout};
use std::slice;

static mut STATE: Option<TokenContract> = None;
static mut MEMORY: *mut u8 = std::ptr::null_mut();
static mut MEMORY_SIZE: usize = 0;

#[no_mangle]
pub extern "C" fn allocate(size: usize) -> *mut u8 {
    unsafe {
        let layout = Layout::from_size_align(size, 8).unwrap();
        let ptr = alloc(layout);
        if ptr.is_null() {
            std::alloc::handle_alloc_error(layout);
        }
        ptr
    }
}

#[no_mangle]
pub extern "C" fn deallocate(ptr: *mut u8, size: usize) {
    unsafe {
        let layout = Layout::from_size_align(size, 8).unwrap();
        dealloc(ptr, layout);
    }
}

#[no_mangle]
pub extern "C" fn init_contract(args_ptr: *const u8, args_len: usize) -> i32 {
    unsafe {
        let args_bytes = slice::from_raw_parts(args_ptr, args_len);
        let args: InitArgs = match borsh::try_from_slice(args_bytes) {
            Ok(args) => args,
            Err(_) => return -1,
        };
        
        let mut contract = TokenContract::new();
        match contract.init(args) {
            Ok(()) => {
                STATE = Some(contract);
                0
            }
            Err(_) => -1,
        }
    }
}

#[no_mangle]
pub extern "C" fn transfer(args_ptr: *const u8, args_len: usize) -> i32 {
    unsafe {
        let args_bytes = slice::from_raw_parts(args_ptr, args_len);
        let args: TransferArgs = match borsh::try_from_slice(args_bytes) {
            Ok(args) => args,
            Err(_) => return -1,
        };
        
        match STATE.as_mut() {
            Some(contract) => match contract.transfer(args) {
                Ok(()) => 0,
                Err(_) => -1,
            },
            None => -1,
        }
    }
}

#[no_mangle]
pub extern "C" fn balance_of(args_ptr: *const u8, args_len: usize) -> i64 {
    unsafe {
        let args_bytes = slice::from_raw_parts(args_ptr, args_len);
        let args: BalanceArgs = match borsh::try_from_slice(args_bytes) {
            Ok(args) => args,
            Err(_) => return -1,
        };
        
        match STATE.as_ref() {
            Some(contract) => match contract.balance_of(args) {
                Ok(balance) => balance as i64,
                Err(_) => -1,
            },
            None => -1,
        }
    }
}

#[no_mangle]
pub extern "C" fn get_state() -> i32 {
    unsafe {
        match STATE.as_ref() {
            Some(contract) => {
                let state_bytes = match borsh::to_vec(&contract.state) {
                    Ok(bytes) => bytes,
                    Err(_) => return -1,
                };
                
                let ptr = allocate(state_bytes.len());
                std::ptr::copy_nonoverlapping(
                    state_bytes.as_ptr(),
                    ptr,
                    state_bytes.len(),
                );
                
                ptr as i32
            }
            None => -1,
        }
    }
}

#[no_mangle]
pub extern "C" fn get_state_size() -> i32 {
    unsafe {
        match STATE.as_ref() {
            Some(contract) => {
                borsh::to_vec(&contract.state)
                    .map(|bytes| bytes.len() as i32)
                    .unwrap_or(-1)
            }
            None => -1,
        }
    }
}
```

---

## 15.2 Polkadot ink!

### Framework ink! para Smart Contracts

O ink! é um framework de linguagem embedida para Rust que permite escrever smart contracts para a blockchain Polkadot e suas parachains.

### Smart Contract Completo com ink!

```rust
// ink-token-contract/lib.rs
#![cfg_attr(not(feature = "std"), no_std, no_main)]

#[ink::contract]
mod token_contract {
    use ink::storage::Mapping;
    
    #[ink(storage)]
    pub struct TokenContract {
        owner: AccountId,
        total_supply: Balance,
        balances: Mapping<AccountId, Balance>,
        name: String,
        symbol: String,
    }
    
    #[derive(Debug, PartialEq, Eq, Clone, scale::Encode, scale::Decode)]
    #[cfg_attr(feature = "std", derive(scale_info::TypeInfo, ink::storage::traits::StorageLayout))]
    pub enum Error {
        InsufficientBalance,
        Unauthorized,
        AlreadyInitialized,
        Overflow,
        InvalidArguments,
    }
    
    impl From<scale::Error> for Error {
        fn from(_: scale::Error) -> Self {
            Error::InvalidArguments
        }
    }
    
    #[ink(event)]
    pub struct Transfer {
        #[ink(topic)]
        from: Option<AccountId>,
        #[ink(topic)]
        to: Option<AccountId>,
        value: Balance,
    }
    
    #[ink(event)]
    pub struct Approval {
        #[ink(topic)]
        owner: AccountId,
        #[ink(topic)]
        spender: AccountId,
        value: Balance,
    }
    
    impl TokenContract {
        #[ink(constructor)]
        pub fn new(name: String, symbol: String, initial_supply: Balance) -> Self {
            let caller = Self::env().caller();
            let mut balances = Mapping::default();
            balances.insert(caller, &initial_supply);
            
            Self::env().emit_event(Transfer {
                from: None,
                to: Some(caller),
                value: initial_supply,
            });
            
            Self {
                owner: caller,
                total_supply: initial_supply,
                balances,
                name,
                symbol,
            }
        }
        
        #[ink(message)]
        pub fn name(&self) -> String {
            self.name.clone()
        }
        
        #[ink(message)]
        pub fn symbol(&self) -> String {
            self.symbol.clone()
        }
        
        #[ink(message)]
        pub fn total_supply(&self) -> Balance {
            self.total_supply
        }
        
        #[ink(message)]
        pub fn balance_of(&self, owner: AccountId) -> Balance {
            self.balances.get(owner).unwrap_or(0)
        }
        
        #[ink(message)]
        pub fn transfer(&mut self, to: AccountId, value: Balance) -> Result<(), Error> {
            let from = self.env().caller();
            let from_balance = self.balance_of(from);
            
            if from_balance < value {
                return Err(Error::InsufficientBalance);
            }
            
            self.balances.insert(from, &(from_balance - value));
            
            let to_balance = self.balance_of(to);
            self.balances
                .insert(to, &(to_balance.checked_add(value).ok_or(Error::Overflow)?));
            
            self.env().emit_event(Transfer {
                from: Some(from),
                to: Some(to),
                value,
            });
            
            Ok(())
        }
        
        #[ink(message)]
        pub fn mint(&mut self, to: AccountId, value: Balance) -> Result<(), Error> {
            if self.env().caller() != self.owner {
                return Err(Error::Unauthorized);
            }
            
            self.total_supply = self
                .total_supply
                .checked_add(value)
                .ok_or(Error::Overflow)?;
            
            let to_balance = self.balance_of(to);
            self.balances
                .insert(to, &(to_balance.checked_add(value).ok_or(Error::Overflow)?));
            
            self.env().emit_event(Transfer {
                from: None,
                to: Some(to),
                value,
            });
            
            Ok(())
        }
        
        #[ink(message)]
        pub fn burn(&mut self, value: Balance) -> Result<(), Error> {
            let from = self.env().caller();
            let from_balance = self.balance_of(from);
            
            if from_balance < value {
                return Err(Error::InsufficientBalance);
            }
            
            self.total_supply = self
                .total_supply
                .checked_sub(value)
                .ok_or(Error::Overflow)?;
            
            self.balances.insert(from, &(from_balance - value));
            
            self.env().emit_event(Transfer {
                from: Some(from),
                to: None,
                value,
            });
            
            Ok(())
        }
        
        #[ink(message)]
        pub fn approve(&mut self, spender: AccountId, value: Balance) -> Result<(), Error> {
            let owner = self.env().caller();
            
            self.env().emit_event(Approval {
                owner,
                spender,
                value,
            });
            
            Ok(())
        }
        
        #[ink(message)]
        pub fn transfer_from(
            &mut self,
            from: AccountId,
            to: AccountId,
            value: Balance,
        ) -> Result<(), Error> {
            let caller = self.env().caller();
            let from_balance = self.balance_of(from);
            
            if from_balance < value {
                return Err(Error::InsufficientBalance);
            }
            
            self.balances.insert(from, &(from_balance - value));
            
            let to_balance = self.balance_of(to);
            self.balances
                .insert(to, &(to_balance.checked_add(value).ok_or(Error::Overflow)?));
            
            self.env().emit_event(Transfer {
                from: Some(from),
                to: Some(to),
                value,
            });
            
            Ok(())
        }
    }
    
    #[cfg(test)]
    mod tests {
        use super::*;
        use ink::env::{test::DefaultAccounts, DefaultEnvironment};
        
        fn default_accounts() -> DefaultAccounts<DefaultEnvironment> {
            ink::env::test::default_accounts::<DefaultEnvironment>()
        }
        
        fn set_caller(caller: AccountId) {
            ink::env::test::set_caller::<DefaultEnvironment>(caller);
        }
        
        #[ink::test]
        fn test_initial_supply() {
            let accounts = default_accounts();
            set_caller(accounts.alice);
            
            let contract = TokenContract::new(
                "Test Token".to_string(),
                "TST".to_string(),
                1000000,
            );
            
            assert_eq!(contract.total_supply(), 1000000);
            assert_eq!(contract.balance_of(accounts.alice), 1000000);
        }
        
        #[ink::test]
        fn test_transfer() {
            let accounts = default_accounts();
            set_caller(accounts.alice);
            
            let mut contract = TokenContract::new(
                "Test Token".to_string(),
                "TST".to_string(),
                1000000,
            );
            
            contract.transfer(accounts.bob, 500).unwrap();
            
            assert_eq!(contract.balance_of(accounts.alice), 999500);
            assert_eq!(contract.balance_of(accounts.bob), 500);
        }
        
        #[ink::test]
        fn test_insufficient_balance() {
            let accounts = default_accounts();
            set_caller(accounts.alice);
            
            let mut contract = TokenContract::new(
                "Test Token".to_string(),
                "TST".to_string(),
                1000,
            );
            
            assert_eq!(
                contract.transfer(accounts.bob, 2000),
                Err(Error::InsufficientBalance)
            );
        }
        
        #[ink::test]
        fn test_mint() {
            let accounts = default_accounts();
            set_caller(accounts.alice);
            
            let mut contract = TokenContract::new(
                "Test Token".to_string(),
                "TST".to_string(),
                1000000,
            );
            
            contract.mint(accounts.bob, 500).unwrap();
            
            assert_eq!(contract.total_supply(), 1000500);
            assert_eq!(contract.balance_of(accounts.bob), 500);
        }
        
        #[ink::test]
        fn test_unauthorized_mint() {
            let accounts = default_accounts();
            set_caller(accounts.alice);
            
            let mut contract = TokenContract::new(
                "Test Token".to_string(),
                "TST".to_string(),
                1000000,
            );
            
            set_caller(accounts.bob);
            
            assert_eq!(contract.mint(accounts.bob, 500), Err(Error::Unauthorized));
        }
    }
}
```

### Configuração do ink!

```toml
# Cargo.toml
[package]
name = "token_contract"
version = "0.1.0"
authors = ["Developer <dev@example.com>"]
edition = "2021"

[dependencies]
ink = { version = "4.3", default-features = false }
scale = { package = "parity-scale-codec", version = "3", default-features = false, features = ["derive"] }
scale-info = { version = "2.9", default-features = false, features = ["derive"], optional = true }

[dev-dependencies]
ink_e2e = { version = "4.3" }

[lib]
name = "token_contract"
path = "lib.rs"

crate-type = [
    "cdylib",
    "rlib",
]

[features]
default = ["std"]
std = [
    "ink/std",
    "scale/std",
    "scale-info/std",
]
ink-as-dependency = []
e2e-tests = []

[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
overflow-checks = true
panic = "abort"
strip = "symbols"
debug = false
debug-assertions = false
```

---

## 15.3 NEAR SDK

### Smart Contracts com NEAR SDK

O NEAR Protocol utiliza WebAssembly como base para seus smart contracts, oferecendo um SDK em Rust que simplifica o desenvolvimento.

### Token NEAR com WASM

```rust
// near-token/src/lib.rs
use near_sdk::borsh::{self, BorshDeserialize, BorshSerialize};
use near_sdk::collections::LookupMap;
use near_sdk::{env, near_bindgen, AccountId, Balance, Promise};

#[near_bindgen]
#[derive(BorshDeserialize, BorshSerialize)]
pub struct TokenContract {
    owner: AccountId,
    total_supply: Balance,
    balances: LookupMap<AccountId, Balance>,
    name: String,
    symbol: String,
}

#[derive(BorshDeserialize, BorshSerialize, Serialize, Deserialize, Clone)]
pub struct AccountInfo {
    pub balance: Balance,
    pub allowances: std::collections::HashMap<AccountId, Balance>,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct InitArgs {
    pub name: String,
    pub symbol: String,
    pub initial_supply: Balance,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct TransferArgs {
    pub receiver_id: AccountId,
    pub amount: Balance,
    pub memo: Option<String>,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct BatchTransferArgs {
    pub transfers: Vec<TransferArgs>,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct FtBalanceOfArgs {
    pub account_id: AccountId,
}

#[derive(BorshDeserialize, BorshSerialize)]
pub struct FtTransferCallArgs {
    pub receiver_id: AccountId,
    pub amount: Balance,
    pub memo: Option<String>,
    pub msg: String,
}

#[near_bindgen]
impl TokenContract {
    #[init]
    pub fn new(name: String, symbol: String, initial_supply: Balance) -> Self {
        let caller = env::predecessor_account_id();
        let mut balances = LookupMap::new(b"a");
        
        balances.insert(&caller, &initial_supply);
        
        env::log_str(&format!(
            "Token initialized: {} ({}) with supply {}",
            name, symbol, initial_supply
        ));
        
        Self {
            owner: caller,
            total_supply: initial_supply,
            balances,
            name,
            symbol,
        }
    }
    
    #[payable]
    pub fn ft_transfer(&mut self, receiver_id: AccountId, amount: Balance, memo: Option<String>) {
        let predecessor = env::predecessor_account_id();
        let attached = env::attached_deposit();
        
        // Require exactly 1 yoctoNEAR for security
        assert_eq!(attached, 1, "Requires 1 yoctoNEAR for security");
        
        let sender_balance = self.balances.get(&predecessor).unwrap_or(0);
        assert!(
            sender_balance >= amount,
            "Insufficient balance: {} < {}",
            sender_balance,
            amount
        );
        
        // Update balances
        self.balances.insert(&predecessor, &(sender_balance - amount));
        
        let receiver_balance = self.balances.get(&receiver_id).unwrap_or(0);
        self.balances
            .insert(&receiver_id, &(receiver_balance + amount));
        
        // Log transfer
        env::log_str(&format!(
            "Transfer: {} -> {} amount: {} memo: {}",
            predecessor,
            receiver_id,
            amount,
            memo.unwrap_or_default()
        ));
    }
    
    #[payable]
    pub fn ft_transfer_call(
        &mut self,
        receiver_id: AccountId,
        amount: Balance,
        memo: Option<String>,
        msg: String,
    ) -> Promise {
        let predecessor = env::predecessor_account_id();
        let attached = env::attached_deposit();
        
        assert_eq!(attached, 1, "Requires 1 yoctoNEAR for security");
        
        let sender_balance = self.balances.get(&predecessor).unwrap_or(0);
        assert!(sender_balance >= amount, "Insufficient balance");
        
        // Update balances
        self.balances.insert(&predecessor, &(sender_balance - amount));
        
        let receiver_balance = self.balances.get(&receiver_id).unwrap_or(0);
        self.balances
            .insert(&receiver_id, &(receiver_balance + amount));
        
        // Log transfer
        env::log_str(&format!(
            "Transfer call: {} -> {} amount: {} msg: {}",
            predecessor, receiver_id, amount, msg
        ));
        
        // In real implementation, would call receiver contract
        Promise::new(receiver_id)
    }
    
    pub fn ft_balance_of(&self, account_id: AccountId) -> Balance {
        self.balances.get(&account_id).unwrap_or(0)
    }
    
    pub fn ft_total_supply(&self) -> Balance {
        self.total_supply
    }
    
    pub fn ft_name(&self) -> String {
        self.name.clone()
    }
    
    pub fn ft_symbol(&self) -> String {
        self.symbol.clone()
    }
    
    #[payable]
    pub fn mint(&mut self, account_id: AccountId, amount: Balance) {
        let predecessor = env::predecessor_account_id();
        assert_eq!(predecessor, self.owner, "Only owner can mint");
        
        let attached = env::attached_deposit();
        assert_eq!(attached, 1, "Requires 1 yoctoNEAR for security");
        
        self.total_supply += amount;
        
        let balance = self.balances.get(&account_id).unwrap_or(0);
        self.balances.insert(&account_id, &(balance + amount));
        
        env::log_str(&format!("Mint: {} amount: {}", account_id, amount));
    }
    
    #[payable]
    pub fn burn(&mut self, amount: Balance) {
        let predecessor = env::predecessor_account_id();
        let attached = env::attached_deposit();
        assert_eq!(attached, 1, "Requires 1 yoctoNEAR for security");
        
        let balance = self.balances.get(&predecessor).unwrap_or(0);
        assert!(balance >= amount, "Insufficient balance");
        
        self.total_supply -= amount;
        self.balances.insert(&predecessor, &(balance - amount));
        
        env::log_str(&format!("Burn: {} amount: {}", predecessor, amount));
    }
    
    pub fn storage_balance_of(&self, account_id: AccountId) -> u128 {
        // Return storage deposit for account
        if self.balances.contains_key(&account_id) {
            env::storage_byte_cost() * 100 // Simplified
        } else {
            0
        }
    }
    
    #[private]
    pub fn on_transfer_returned(&mut self, sender_id: AccountId, amount: Balance) {
        // Handle returned tokens from failed cross-contract call
        let balance = self.balances.get(&sender_id).unwrap_or(0);
        self.balances.insert(&sender_id, &(balance + amount));
        
        env::log_str(&format!(
            "Transfer returned: {} amount: {}",
            sender_id, amount
        ));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use near_sdk::test_utils::{accounts, VMContextBuilder};
    use near_sdk::testing_env;
    
    fn get_context(predecessor: AccountId, deposit: u128) -> VMContextBuilder {
        let mut builder = VMContextBuilder::new();
        builder
            .predecessor_account_id(predecessor)
            .attached_deposit(deposit)
            .build();
        builder
    }
    
    #[test]
    fn test_new() {
        let context = get_context(accounts(0), 0);
        testing_env!(context.build());
        
        let contract = TokenContract::new(
            "Test Token".to_string(),
            "TST".to_string(),
            1000000,
        );
        
        assert_eq!(contract.ft_total_supply(), 1000000);
        assert_eq!(contract.ft_balance_of(accounts(0)), 1000000);
    }
    
    #[test]
    fn test_transfer() {
        let context = get_context(accounts(0), 1);
        testing_env!(context.build());
        
        let mut contract = TokenContract::new(
            "Test Token".to_string(),
            "TST".to_string(),
            1000000,
        );
        
        contract.ft_transfer(accounts(1), 500, None);
        
        assert_eq!(contract.ft_balance_of(accounts(0)), 999500);
        assert_eq!(contract.ft_balance_of(accounts(1)), 500);
    }
    
    #[test]
    #[should_panic(expected = "Insufficient balance")]
    fn test_insufficient_balance() {
        let context = get_context(accounts(0), 1);
        testing_env!(context.build());
        
        let mut contract = TokenContract::new(
            "Test Token".to_string(),
            "TST".to_string(),
            1000,
        );
        
        contract.ft_transfer(accounts(1), 2000, None);
    }
    
    #[test]
    fn test_mint() {
        let context = get_context(accounts(0), 1);
        testing_env!(context.build());
        
        let mut contract = TokenContract::new(
            "Test Token".to_string(),
            "TST".to_string(),
            1000000,
        );
        
        contract.mint(accounts(1), 500);
        
        assert_eq!(contract.ft_total_supply(), 1000500);
        assert_eq!(contract.ft_balance_of(accounts(1)), 500);
    }
    
    #[test]
    #[should_panic(expected = "Only owner can mint")]
    fn test_unauthorized_mint() {
        let context = get_context(accounts(0), 1);
        testing_env!(context.build());
        
        let mut contract = TokenContract::new(
            "Test Token".to_string(),
            "TST".to_string(),
            1000000,
        );
        
        // Switch to non-owner
        let context = get_context(accounts(1), 1);
        testing_env!(context.build());
        
        contract.mint(accounts(1), 500);
    }
}
```

---

## 15.4 Cosmos CosmWasm

### Smart Contracts com CosmWasm

O CosmWasm é uma implementação de WebAssembly para o Cosmos SDK, permitindo a criação de smart contracts interoperáveis entre diferentes blockchains no ecossistema Cosmos.

### Token CosmWasm

```rust
// cosmwasm-token/src/lib.rs
use cosmwasm_std::{
    entry_point, to_binary, Binary, Deps, DepsMut, Env, MessageInfo,
    Response, StdResult, Uint128,
};
use cw_storage_plus::Map;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct InstantiateMsg {
    pub name: String,
    pub symbol: String,
    pub initial_supply: Uint128,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub enum ExecuteMsg {
    Transfer {
        recipient: String,
        amount: Uint128,
    },
    Mint {
        recipient: String,
        amount: Uint128,
    },
    Burn {
        amount: Uint128,
    },
    Approve {
        spender: String,
        amount: Uint128,
    },
    TransferFrom {
        owner: String,
        recipient: String,
        amount: Uint128,
    },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub enum QueryMsg {
    Balance { address: String },
    TotalSupply,
    Name,
    Symbol,
    Allowance { owner: String, spender: String },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct BalanceResponse {
    pub balance: Uint128,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct TotalSupplyResponse {
    pub total_supply: Uint128,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct NameResponse {
    pub name: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct SymbolResponse {
    pub symbol: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct AllowanceResponse {
    pub allowance: Uint128,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct TokenInfo {
    pub name: String,
    pub symbol: String,
    pub total_supply: Uint128,
    pub owner: String,
}

pub const BALANCES: Map<&str, Uint128> = Map::new("balances");
pub const ALLOWANCES: Map<(&str, &str), Uint128> = Map::new("allowances");
pub const TOKEN_INFO: Map<&str, TokenInfo> = Map::new("token_info");

#[entry_point]
pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    msg: InstantiateMsg,
) -> StdResult<Response> {
    let token_info = TokenInfo {
        name: msg.name.clone(),
        symbol: msg.symbol.clone(),
        total_supply: msg.initial_supply,
        owner: info.sender.to_string(),
    };
    
    TOKEN_INFO.save(deps.storage, "info", &token_info)?;
    BALANCES.save(deps.storage, info.sender.as_str(), &msg.initial_supply)?;
    
    Ok(Response::new()
        .add_attribute("action", "instantiate")
        .add_attribute("name", msg.name)
        .add_attribute("symbol", msg.symbol)
        .add_attribute("initial_supply", msg.initial_supply))
}

#[entry_point]
pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> StdResult<Response> {
    match msg {
        ExecuteMsg::Transfer { recipient, amount } => {
            execute_transfer(deps, info, recipient, amount)
        }
        ExecuteMsg::Mint { recipient, amount } => {
            execute_mint(deps, info, recipient, amount)
        }
        ExecuteMsg::Burn { amount } => execute_burn(deps, info, amount),
        ExecuteMsg::Approve { spender, amount } => {
            execute_approve(deps, info, spender, amount)
        }
        ExecuteMsg::TransferFrom {
            owner,
            recipient,
            amount,
        } => execute_transfer_from(deps, info, owner, recipient, amount),
    }
}

fn execute_transfer(
    deps: DepsMut,
    info: MessageInfo,
    recipient: String,
    amount: Uint128,
) -> StdResult<Response> {
    let sender_balance = BALANCES
        .may_load(deps.storage, info.sender.as_str())?
        .unwrap_or_default();
    
    if sender_balance < amount {
        return Err(cosmwasm_std::StdError::generic_err(
            "Insufficient balance",
        ));
    }
    
    BALANCES.save(
        deps.storage,
        info.sender.as_str(),
        &(sender_balance - amount),
    )?;
    
    let recipient_balance = BALANCES
        .may_load(deps.storage, &recipient)?
        .unwrap_or_default();
    
    BALANCES.save(deps.storage, &recipient, &(recipient_balance + amount))?;
    
    Ok(Response::new()
        .add_attribute("action", "transfer")
        .add_attribute("from", info.sender)
        .add_attribute("to", recipient)
        .add_attribute("amount", amount))
}

fn execute_mint(
    deps: DepsMut,
    info: MessageInfo,
    recipient: String,
    amount: Uint128,
) -> StdResult<Response> {
    let token_info = TOKEN_INFO.load(deps.storage, "info")?;
    
    if info.sender != token_info.owner {
        return Err(cosmwasm_std::StdError::generic_err("Unauthorized"));
    }
    
    let new_total_supply = token_info.total_supply + amount;
    TOKEN_INFO.save(
        deps.storage,
        "info",
        &TokenInfo {
            total_supply: new_total_supply,
            ..token_info
        },
    )?;
    
    let recipient_balance = BALANCES
        .may_load(deps.storage, &recipient)?
        .unwrap_or_default();
    
    BALANCES.save(deps.storage, &recipient, &(recipient_balance + amount))?;
    
    Ok(Response::new()
        .add_attribute("action", "mint")
        .add_attribute("to", recipient)
        .add_attribute("amount", amount))
}

fn execute_burn(deps: DepsMut, info: MessageInfo, amount: Uint128) -> StdResult<Response> {
    let sender_balance = BALANCES
        .may_load(deps.storage, info.sender.as_str())?
        .unwrap_or_default();
    
    if sender_balance < amount {
        return Err(cosmwasm_std::StdError::generic_err(
            "Insufficient balance",
        ));
    }
    
    BALANCES.save(
        deps.storage,
        info.sender.as_str(),
        &(sender_balance - amount),
    )?;
    
    let mut token_info = TOKEN_INFO.load(deps.storage, "info")?;
    token_info.total_supply = token_info.total_supply - amount;
    TOKEN_INFO.save(deps.storage, "info", &token_info)?;
    
    Ok(Response::new()
        .add_attribute("action", "burn")
        .add_attribute("from", info.sender)
        .add_attribute("amount", amount))
}

fn execute_approve(
    deps: DepsMut,
    info: MessageInfo,
    spender: String,
    amount: Uint128,
) -> StdResult<Response> {
    ALLOWANCES.save(
        deps.storage,
        (info.sender.as_str(), spender.as_str()),
        &amount,
    )?;
    
    Ok(Response::new()
        .add_attribute("action", "approve")
        .add_attribute("owner", info.sender)
        .add_attribute("spender", spender)
        .add_attribute("amount", amount))
}

fn execute_transfer_from(
    deps: DepsMut,
    info: MessageInfo,
    owner: String,
    recipient: String,
    amount: Uint128,
) -> StdResult<Response> {
    let allowance = ALLOWANCES
        .may_load(deps.storage, (owner.as_str(), info.sender.as_str()))?
        .unwrap_or_default();
    
    if allowance < amount {
        return Err(cosmwasm_std::StdError::generic_err("Allowance exceeded"));
    }
    
    ALLOWANCES.save(
        deps.storage,
        (owner.as_str(), info.sender.as_str()),
        &(allowance - amount),
    )?;
    
    let owner_balance = BALANCES
        .may_load(deps.storage, &owner)?
        .unwrap_or_default();
    
    if owner_balance < amount {
        return Err(cosmwasm_std::StdError::generic_err(
            "Insufficient balance",
        ));
    }
    
    BALANCES.save(deps.storage, &owner, &(owner_balance - amount))?;
    
    let recipient_balance = BALANCES
        .may_load(deps.storage, &recipient)?
        .unwrap_or_default();
    
    BALANCES.save(deps.storage, &recipient, &(recipient_balance + amount))?;
    
    Ok(Response::new()
        .add_attribute("action", "transfer_from")
        .add_attribute("from", owner)
        .add_attribute("to", recipient)
        .add_attribute("by", info.sender)
        .add_attribute("amount", amount))
}

#[entry_point]
pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::Balance { address } => to_binary(&query_balance(deps, address)?),
        QueryMsg::TotalSupply => to_binary(&query_total_supply(deps)?),
        QueryMsg::Name => to_binary(&query_name(deps)?),
        QueryMsg::Symbol => to_binary(&query_symbol(deps)?),
        QueryMsg::Allowance { owner, spender } => {
            to_binary(&query_allowance(deps, owner, spender)?)
        }
    }
}

fn query_balance(deps: Deps, address: String) -> StdResult<BalanceResponse> {
    let balance = BALANCES
        .may_load(deps.storage, &address)?
        .unwrap_or_default();
    
    Ok(BalanceResponse { balance })
}

fn query_total_supply(deps: Deps) -> StdResult<TotalSupplyResponse> {
    let token_info = TOKEN_INFO.load(deps.storage, "info")?;
    
    Ok(TotalSupplyResponse {
        total_supply: token_info.total_supply,
    })
}

fn query_name(deps: Deps) -> StdResult<NameResponse> {
    let token_info = TOKEN_INFO.load(deps.storage, "info")?;
    
    Ok(NameResponse {
        name: token_info.name,
    })
}

fn query_symbol(deps: Deps) -> StdResult<SymbolResponse> {
    let token_info = TOKEN_INFO.load(deps.storage, "info")?;
    
    Ok(SymbolResponse {
        symbol: token_info.symbol,
    })
}

fn query_allowance(deps: Deps, owner: String, spender: String) -> StdResult<AllowanceResponse> {
    let allowance = ALLOWANCES
        .may_load(deps.storage, (&owner, &spender))?
        .unwrap_or_default();
    
    Ok(AllowanceResponse { allowance })
}

#[cfg(test)]
mod tests {
    use super::*;
    use cosmwasm_std::testing::{mock_dependencies, mock_env, mock_info};
    use cosmwasm_std::{from_binary, Uint128};
    
    #[test]
    fn test_instantiate() {
        let mut deps = mock_dependencies();
        let env = mock_env();
        let info = mock_info("creator", &[]);
        
        let msg = InstantiateMsg {
            name: "Test Token".to_string(),
            symbol: "TST".to_string(),
            initial_supply: Uint128::new(1000000),
        };
        
        let res = instantiate(deps.as_mut(), env, info, msg).unwrap();
        assert_eq!(res.attributes.len(), 4);
        
        // Check total supply
        let res = query(deps.as_ref(), mock_env(), QueryMsg::TotalSupply).unwrap();
        let total_supply: TotalSupplyResponse = from_binary(&res).unwrap();
        assert_eq!(total_supply.total_supply, Uint128::new(1000000));
        
        // Check creator balance
        let res = query(
            deps.as_ref(),
            mock_env(),
            QueryMsg::Balance {
                address: "creator".to_string(),
            },
        )
        .unwrap();
        let balance: BalanceResponse = from_binary(&res).unwrap();
        assert_eq!(balance.balance, Uint128::new(1000000));
    }
    
    #[test]
    fn test_transfer() {
        let mut deps = mock_dependencies();
        let env = mock_env();
        let info = mock_info("creator", &[]);
        
        let msg = InstantiateMsg {
            name: "Test Token".to_string(),
            symbol: "TST".to_string(),
            initial_supply: Uint128::new(1000000),
        };
        
        instantiate(deps.as_mut(), env.clone(), info.clone(), msg).unwrap();
        
        let msg = ExecuteMsg::Transfer {
            recipient: "recipient".to_string(),
            amount: Uint128::new(500),
        };
        
        let res = execute(deps.as_mut(), env, info, msg).unwrap();
        assert_eq!(res.attributes.len(), 4);
        
        // Check balances
        let res = query(
            deps.as_ref(),
            mock_env(),
            QueryMsg::Balance {
                address: "creator".to_string(),
            },
        )
        .unwrap();
        let balance: BalanceResponse = from_binary(&res).unwrap();
        assert_eq!(balance.balance, Uint128::new(999500));
        
        let res = query(
            deps.as_ref(),
            mock_env(),
            QueryMsg::Balance {
                address: "recipient".to_string(),
            },
        )
        .unwrap();
        let balance: BalanceResponse = from_binary(&res).unwrap();
        assert_eq!(balance.balance, Uint128::new(500));
    }
    
    #[test]
    fn test_insufficient_balance() {
        let mut deps = mock_dependencies();
        let env = mock_env();
        let info = mock_info("creator", &[]);
        
        let msg = InstantiateMsg {
            name: "Test Token".to_string(),
            symbol: "TST".to_string(),
            initial_supply: Uint128::new(1000),
        };
        
        instantiate(deps.as_mut(), env.clone(), info.clone(), msg).unwrap();
        
        let msg = ExecuteMsg::Transfer {
            recipient: "recipient".to_string(),
            amount: Uint128::new(2000),
        };
        
        let err = execute(deps.as_mut(), env, info, msg).unwrap_err();
        assert!(err.to_string().contains("Insufficient balance"));
    }
}
```

---

## 15.5 Ethereum eWASM

### Ethereum WebAssembly (eWASM)

O eWASM é uma proposta para substituir a EVM pelo WebAssembly no Ethereum, oferecendo compatibilidade com smart contracts existentes enquanto permite o uso de WASM nativo.

### Compilador Solidity para WASM

```rust
// ewasm-compiler/src/lib.rs
use std::collections::HashMap;

pub struct EwasmCompiler {
    solidity_parser: SolidityParser,
    wasm_generator: WasmGenerator,
    optimizer: WasmOptimizer,
}

impl EwasmCompiler {
    pub fn new() -> Self {
        Self {
            solidity_parser: SolidityParser::new(),
            wasm_generator: WasmGenerator::new(),
            optimizer: WasmOptimizer::new(),
        }
    }
    
    pub fn compile(&self, source: &str) -> Result<CompiledContract, CompileError> {
        // Parse Solidity
        let ast = self.solidity_parser.parse(source)?;
        
        // Generate WASM
        let mut wasm_module = self.wasm_generator.generate(&ast)?;
        
        // Optimize
        wasm_module = self.optimizer.optimize(wasm_module);
        
        // Validate
        self.validate_wasm(&wasm_module)?;
        
        Ok(CompiledContract {
            wasm_module,
            abi: self.generate_abi(&ast),
            bytecode: self.generate_bytecode(&wasm_module),
        })
    }
    
    fn validate_wasm(&self, module: &[u8]) -> Result<(), CompileError> {
        // Validate WASM module
        wasmparser::validate(module)
            .map_err(|e| CompileError::InvalidWasm(e.to_string()))?;
        
        Ok(())
    }
    
    fn generate_abi(&self, ast: &SolidityAST) -> Vec<ABIEntry> {
        // Generate ABI from AST
        vec![]
    }
    
    fn generate_bytecode(&self, module: &[u8]) -> String {
        hex::encode(module)
    }
}

pub struct CompiledContract {
    pub wasm_module: Vec<u8>,
    pub abi: Vec<ABIEntry>,
    pub bytecode: String,
}

pub enum CompileError {
    ParseError(String),
    CodeGenError(String),
    InvalidWasm(String),
    OptimizationError(String),
}

pub struct SolidityParser {
    tokens: Vec<Token>,
}

impl SolidityParser {
    pub fn new() -> Self {
        Self {
            tokens: Vec::new(),
        }
    }
    
    pub fn parse(&self, source: &str) -> Result<SolidityAST, CompileError> {
        // Tokenize
        let tokens = self.tokenize(source)?;
        
        // Parse tokens into AST
        let ast = self.parse_tokens(&tokens)?;
        
        Ok(ast)
    }
    
    fn tokenize(&self, source: &str) -> Result<Vec<Token>, CompileError> {
        // Tokenization logic
        Ok(vec![])
    }
    
    fn parse_tokens(&self, tokens: &[Token]) -> Result<SolidityAST, CompileError> {
        // Parsing logic
        Ok(SolidityAST {
            contracts: vec![],
            interfaces: vec![],
            libraries: vec![],
        })
    }
}

pub struct WasmGenerator {
    instruction_set: InstructionSet,
}

impl WasmGenerator {
    pub fn new() -> Self {
        Self {
            instruction_set: InstructionSet::new(),
        }
    }
    
    pub fn generate(&self, ast: &SolidityAST) -> Result<Vec<u8>, CompileError> {
        let mut module = WasmModule::new();
        
        // Generate memory section
        module.add_memory(256, Some(1024));
        
        // Generate imports for Ethereum host functions
        module.add_import("env", "call", FunctionType::new(
            vec![ValType::I32, ValType::I32, ValType::I32, ValType::I32],
            vec![ValType::I32],
        ));
        
        module.add_import("env", "storage_load", FunctionType::new(
            vec![ValType::I32, ValType::I32],
            vec![ValType::I32],
        ));
        
        module.add_import("env", "storage_store", FunctionType::new(
            vec![ValType::I32, ValType::I32, ValType::I32],
            vec![],
        ));
        
        // Generate code for each contract
        for contract in &ast.contracts {
            self.generate_contract(&mut module, contract)?;
        }
        
        // Serialize to bytes
        module.serialize()
    }
    
    fn generate_contract(
        &self,
        module: &mut WasmModule,
        contract: &Contract,
    ) -> Result<(), CompileError> {
        // Generate functions for each contract method
        for function in &contract.functions {
            self.generate_function(module, function)?;
        }
        
        // Generate constructor
        if let Some(constructor) = &contract.constructor {
            self.generate_constructor(module, constructor)?;
        }
        
        Ok(())
    }
    
    fn generate_function(
        &self,
        module: &mut WasmModule,
        function: &Function,
    ) -> Result<(), CompileError> {
        // Generate function body
        let mut body = FunctionBody::new();
        
        // Add function locals
        for local in &function.locals {
            body.add_local(local.typ.clone());
        }
        
        // Generate instructions for function body
        for statement in &function.body {
            self.generate_statement(&mut body, statement)?;
        }
        
        // Add return instruction
        body.add_instruction(Instruction::Return);
        
        // Add function to module
        module.add_function(
            FunctionType::new(
                function.parameters.iter().map(|p| p.typ.clone()).collect(),
                function.return_type.iter().cloned().collect(),
            ),
            body,
        );
        
        Ok(())
    }
    
    fn generate_statement(
        &self,
        body: &mut FunctionBody,
        statement: &Statement,
    ) -> Result<(), CompileError> {
        match statement {
            Statement::VariableDeclaration(var) => {
                // Variable declaration
                body.add_instruction(Instruction::I32Const(0));
                body.add_instruction(Instruction::LocalSet(var.index));
            }
            Statement::Assignment(assignment) => {
                // Assignment
                self.generate_expression(body, &assignment.value)?;
                body.add_instruction(Instruction::LocalSet(assignment.target_index));
            }
            Statement::If(if_stmt) => {
                // If statement
                self.generate_expression(body, &if_stmt.condition)?;
                body.add_instruction(Instruction::If(BlockType::Empty));
                for stmt in &if_stmt.then_body {
                    self.generate_statement(body, stmt)?;
                }
                if let Some(else_body) = &if_stmt.else_body {
                    body.add_instruction(Instruction::Else);
                    for stmt in else_body {
                        self.generate_statement(body, stmt)?;
                    }
                }
                body.add_instruction(Instruction::End);
            }
            Statement::Return(ret) => {
                // Return statement
                if let Some(value) = &ret.value {
                    self.generate_expression(body, value)?;
                }
                body.add_instruction(Instruction::Return);
            }
            Statement::Expression(expr) => {
                self.generate_expression(body, expr)?;
            }
        }
        
        Ok(())
    }
    
    fn generate_expression(
        &self,
        body: &mut FunctionBody,
        expression: &Expression,
    ) -> Result<(), CompileError> {
        match expression {
            Expression::Literal(lit) => {
                match lit {
                    Literal::Integer(val) => {
                        body.add_instruction(Instruction::I64Const(*val));
                    }
                    Literal::Boolean(val) => {
                        body.add_instruction(Instruction::I32Const(if *val { 1 } else { 0 }));
                    }
                    _ => {}
                }
            }
            Expression::Variable(var) => {
                body.add_instruction(Instruction::LocalGet(var.index));
            }
            Expression::BinaryOp(op) => {
                self.generate_expression(body, &op.left)?;
                self.generate_expression(body, &op.right)?;
                match op.operator {
                    BinaryOperator::Add => body.add_instruction(Instruction::I64Add),
                    BinaryOperator::Subtract => body.add_instruction(Instruction::I64Sub),
                    BinaryOperator::Multiply => body.add_instruction(Instruction::I64Mul),
                    BinaryOperator::Divide => body.add_instruction(Instruction::I64DivS),
                    BinaryOperator::Equal => {
                        body.add_instruction(Instruction::I64Eq);
                        body.add_instruction(Instruction::I32WrapI64);
                    }
                    _ => {}
                }
            }
            Expression::FunctionCall(call) => {
                // Generate arguments
                for arg in &call.arguments {
                    self.generate_expression(body, arg)?;
                }
                // Call function
                body.add_instruction(Instruction::Call(call.function_index));
            }
            _ => {}
        }
        
        Ok(())
    }
    
    fn generate_constructor(
        &self,
        module: &mut WasmModule,
        constructor: &Constructor,
    ) -> Result<(), CompileError> {
        // Generate constructor function
        let mut body = FunctionBody::new();
        
        // Add parameters
        for param in &constructor.parameters {
            body.add_local(param.typ.clone());
        }
        
        // Generate initialization code
        for statement in &constructor.body {
            self.generate_statement(&mut body, statement)?;
        }
        
        body.add_instruction(Instruction::End);
        
        // Add constructor to module
        module.add_function(
            FunctionType::new(
                constructor.parameters.iter().map(|p| p.typ.clone()).collect(),
                vec![],
            ),
            body,
        );
        
        Ok(())
    }
}

pub struct WasmModule {
    memory: MemorySection,
    imports: Vec<Import>,
    functions: Vec<Function>,
    exports: Vec<Export>,
}

impl WasmModule {
    pub fn new() -> Self {
        Self {
            memory: MemorySection::new(),
            imports: Vec::new(),
            functions: Vec::new(),
            exports: Vec::new(),
        }
    }
    
    pub fn add_memory(&mut self, initial: u32, maximum: Option<u32>) {
        self.memory = MemorySection::new(initial, maximum);
    }
    
    pub fn add_import(&mut self, module: &str, name: &str, func_type: FunctionType) {
        self.imports.push(Import {
            module: module.to_string(),
            name: name.to_string(),
            kind: ImportKind::Function(func_type),
        });
    }
    
    pub fn add_function(&mut self, func_type: FunctionType, body: FunctionBody) {
        self.functions.push(Function {
            type_index: self.functions.len() as u32,
            func_type,
            body,
        });
    }
    
    pub fn serialize(&self) -> Result<Vec<u8>, CompileError> {
        // Serialize to WASM binary format
        let mut buffer = Vec::new();
        
        // Magic number and version
        buffer.extend_from_slice(&[0x00, 0x61, 0x73, 0x6d]);
        buffer.extend_from_slice(&[0x01, 0x00, 0x00, 0x00]);
        
        // Type section
        buffer.push(0x01);
        let type_section = self.serialize_type_section();
        buffer.extend_from_slice(&(type_section.len() as u32).to_le_bytes());
        buffer.extend_from_slice(&type_section);
        
        // Import section
        buffer.push(0x02);
        let import_section = self.serialize_import_section();
        buffer.extend_from_slice(&(import_section.len() as u32).to_le_bytes());
        buffer.extend_from_slice(&import_section);
        
        // Function section
        buffer.push(0x03);
        let func_section = self.serialize_function_section();
        buffer.extend_from_slice(&(func_section.len() as u32).to_le_bytes());
        buffer.extend_from_slice(&func_section);
        
        // Memory section
        buffer.push(0x05);
        let memory_section = self.serialize_memory_section();
        buffer.extend_from_slice(&(memory_section.len() as u32).to_le_bytes());
        buffer.extend_from_slice(&memory_section);
        
        // Code section
        buffer.push(0x0a);
        let code_section = self.serialize_code_section();
        buffer.extend_from_slice(&(code_section.len() as u32).to_le_bytes());
        buffer.extend_from_slice(&code_section);
        
        Ok(buffer)
    }
    
    fn serialize_type_section(&self) -> Vec<u8> {
        let mut section = Vec::new();
        section.push(self.functions.len() as u8);
        
        for func in &self.functions {
            section.extend_from_slice(&func.func_type.serialize());
        }
        
        section
    }
    
    fn serialize_import_section(&self) -> Vec<u8> {
        let mut section = Vec::new();
        section.push(self.imports.len() as u8);
        
        for import in &self.imports {
            section.extend_from_slice(&import.serialize());
        }
        
        section
    }
    
    fn serialize_function_section(&self) -> Vec<u8> {
        let mut section = Vec::new();
        section.push(self.functions.len() as u8);
        
        for func in &self.functions {
            section.extend_from_slice(&func.type_index.to_le_bytes());
        }
        
        section
    }
    
    fn serialize_memory_section(&self) -> Vec<u8> {
        self.memory.serialize()
    }
    
    fn serialize_code_section(&self) -> Vec<u8> {
        let mut section = Vec::new();
        section.push(self.functions.len() as u8);
        
        for func in &self.functions {
            let body = func.body.serialize();
            section.extend_from_slice(&(body.len() as u32).to_le_bytes());
            section.extend_from_slice(&body);
        }
        
        section
    }
}

pub struct WasmOptimizer;

impl WasmOptimizer {
    pub fn new() -> Self {
        Self
    }
    
    pub fn optimize(&self, module: Vec<u8>) -> Vec<u8> {
        // Apply optimizations
        let mut optimized = module;
        
        // Remove dead code
        optimized = self.remove_dead_code(optimized);
        
        // Constant folding
        optimized = self.constant_folding(optimized);
        
        // Peephole optimization
        optimized = self.peephole_optimization(optimized);
        
        optimized
    }
    
    fn remove_dead_code(&self, module: Vec<u8>) -> Vec<u8> {
        // Dead code elimination
        module
    }
    
    fn constant_folding(&self, module: Vec<u8>) -> Vec<u8> {
        // Constant folding optimization
        module
    }
    
    fn peephole_optimization(&self, module: Vec<u8>) -> Vec<u8> {
        // Peephole optimization
        module
    }
}

pub struct ABIEntry {
    pub name: String,
    pub inputs: Vec<ABIParameter>,
    pub outputs: Vec<ABIParameter>,
    pub state_mutability: StateMutability,
}

pub struct ABIParameter {
    pub name: String,
    pub typ: String,
    pub indexed: bool,
}

pub enum StateMutability {
    Pure,
    View,
    NonPayable,
    Payable,
}

pub enum Token {
    Keyword(String),
    Identifier(String),
    Number(String),
    String(String),
    Symbol(char),
    EOF,
}

pub struct SolidityAST {
    pub contracts: Vec<Contract>,
    pub interfaces: Vec<Interface>,
    pub libraries: Vec<Library>,
}

pub struct Contract {
    pub name: String,
    pub constructor: Option<Constructor>,
    pub functions: Vec<Function>,
    pub state_variables: Vec<StateVariable>,
}

pub struct Interface {
    pub name: String,
    pub functions: Vec<FunctionSignature>,
}

pub struct Library {
    pub name: String,
    pub functions: Vec<Function>,
}

pub struct Constructor {
    pub parameters: Vec<Parameter>,
    pub body: Vec<Statement>,
}

pub struct Function {
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub return_type: Vec<ValType>,
    pub locals: Vec<Local>,
    pub body: Vec<Statement>,
    pub visibility: Visibility,
    pub state_mutability: StateMutability,
}

pub struct FunctionSignature {
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub return_type: Vec<ValType>,
}

pub struct Parameter {
    pub name: String,
    pub typ: ValType,
}

pub struct Local {
    pub index: u32,
    pub typ: ValType,
}

pub struct StateVariable {
    pub name: String,
    pub typ: ValType,
    pub visibility: Visibility,
}

pub enum Statement {
    VariableDeclaration(VariableDeclaration),
    Assignment(Assignment),
    If(IfStatement),
    Return(ReturnStatement),
    Expression(Expression),
}

pub struct VariableDeclaration {
    pub name: String,
    pub index: u32,
    pub typ: ValType,
    pub initial_value: Option<Expression>,
}

pub struct Assignment {
    pub target: String,
    pub target_index: u32,
    pub value: Expression,
}

pub struct IfStatement {
    pub condition: Expression,
    pub then_body: Vec<Statement>,
    pub else_body: Option<Vec<Statement>>,
}

pub struct ReturnStatement {
    pub value: Option<Expression>,
}

pub enum Expression {
    Literal(Literal),
    Variable(Variable),
    BinaryOp(BinaryOperation),
    UnaryOp(UnaryOperation),
    FunctionCall(FunctionCall),
    MemberAccess(MemberAccess),
}

pub enum Literal {
    Integer(i64),
    Boolean(bool),
    String(String),
    Address(String),
}

pub struct Variable {
    pub name: String,
    pub index: u32,
}

pub struct BinaryOperation {
    pub left: Box<Expression>,
    pub operator: BinaryOperator,
    pub right: Box<Expression>,
}

pub struct UnaryOperation {
    pub operator: UnaryOperator,
    pub operand: Box<Expression>,
}

pub struct FunctionCall {
    pub function_name: String,
    pub function_index: u32,
    pub arguments: Vec<Expression>,
}

pub struct MemberAccess {
    pub object: Box<Expression>,
    pub member: String,
}

pub enum BinaryOperator {
    Add,
    Subtract,
    Multiply,
    Divide,
    Modulo,
    Equal,
    NotEqual,
    LessThan,
    GreaterThan,
    LessThanOrEqual,
    GreaterThanOrEqual,
    And,
    Or,
    BitwiseAnd,
    BitwiseOr,
    BitwiseXor,
    ShiftLeft,
    ShiftRight,
}

pub enum UnaryOperator {
    Negate,
    Not,
    BitwiseNot,
}

pub enum Visibility {
    Public,
    Private,
    Internal,
    External,
}

pub enum ValType {
    I32,
    I64,
    F32,
    F64,
}

pub struct InstructionSet;

impl InstructionSet {
    pub fn new() -> Self {
        Self
    }
}

pub enum Instruction {
    Nop,
    Block(BlockType),
    Loop(BlockType),
    If(BlockType),
    Else,
    End,
    Br(u32),
    BrIf(u32),
    Return,
    Call(u32),
    LocalGet(u32),
    LocalSet(u32),
    LocalTee(u32),
    I32Const(i32),
    I64Const(i64),
    F32Const(f32),
    F64Const(f64),
    I32Add,
    I32Sub,
    I32Mul,
    I32DivS,
    I64Add,
    I64Sub,
    I64Mul,
    I64DivS,
    I64Eq,
    I64Ne,
    I64LtS,
    I64GtS,
    I32WrapI64,
}

pub enum BlockType {
    Empty,
    Value(ValType),
}

pub struct FunctionBody {
    locals: Vec<ValType>,
    instructions: Vec<Instruction>,
}

impl FunctionBody {
    pub fn new() -> Self {
        Self {
            locals: Vec::new(),
            instructions: Vec::new(),
        }
    }
    
    pub fn add_local(&mut self, typ: ValType) {
        self.locals.push(typ);
    }
    
    pub fn add_instruction(&mut self, instruction: Instruction) {
        self.instructions.push(instruction);
    }
    
    pub fn serialize(&self) -> Vec<u8> {
        let mut buffer = Vec::new();
        
        // Local declarations
        let mut local_groups: Vec<(u32, ValType)> = Vec::new();
        let mut current_type: Option<ValType> = None;
        let mut count = 0;
        
        for local in &self.locals {
            match current_type {
                Some(t) if std::mem::discriminant(&t) == std::mem::discriminant(local) => {
                    count += 1;
                }
                _ => {
                    if let Some(t) = current_type {
                        local_groups.push((count, t));
                    }
                    current_type = Some(local.clone());
                    count = 1;
                }
            }
        }
        
        if let Some(t) = current_type {
            local_groups.push((count, t));
        }
        
        buffer.push(local_groups.len() as u8);
        for (count, typ) in &local_groups {
            buffer.extend_from_slice(&count.to_le_bytes());
            buffer.push(typ.to_u8());
        }
        
        // Instructions
        for instruction in &self.instructions {
            buffer.extend_from_slice(&instruction.serialize());
        }
        
        buffer
    }
}

impl Instruction {
    pub fn serialize(&self) -> Vec<u8> {
        match self {
            Instruction::Nop => vec![0x01],
            Instruction::Block(bt) => {
                let mut buf = vec![0x02];
                buf.extend_from_slice(&bt.serialize());
                buf
            }
            Instruction::Loop(bt) => {
                let mut buf = vec![0x03];
                buf.extend_from_slice(&bt.serialize());
                buf
            }
            Instruction::If(bt) => {
                let mut buf = vec![0x04];
                buf.extend_from_slice(&bt.serialize());
                buf
            }
            Instruction::Else => vec![0x05],
            Instruction::End => vec![0x0b],
            Instruction::Br(l) => {
                let mut buf = vec![0x0c];
                buf.extend_from_slice(&l.to_le_bytes());
                buf
            }
            Instruction::BrIf(l) => {
                let mut buf = vec![0x0d];
                buf.extend_from_slice(&l.to_le_bytes());
                buf
            }
            Instruction::Return => vec![0x0f],
            Instruction::Call(idx) => {
                let mut buf = vec![0x10];
                buf.extend_from_slice(&idx.to_le_bytes());
                buf
            }
            Instruction::LocalGet(idx) => {
                let mut buf = vec![0x20];
                buf.extend_from_slice(&idx.to_le_bytes());
                buf
            }
            Instruction::LocalSet(idx) => {
                let mut buf = vec![0x21];
                buf.extend_from_slice(&idx.to_le_bytes());
                buf
            }
            Instruction::LocalTee(idx) => {
                let mut buf = vec![0x22];
                buf.extend_from_slice(&idx.to_le_bytes());
                buf
            }
            Instruction::I32Const(val) => {
                let mut buf = vec![0x41];
                buf.extend_from_slice(&val.to_le_bytes());
                buf
            }
            Instruction::I64Const(val) => {
                let mut buf = vec![0x42];
                buf.extend_from_slice(&val.to_le_bytes());
                buf
            }
            Instruction::I32Add => vec![0x6a],
            Instruction::I32Sub => vec![0x6b],
            Instruction::I32Mul => vec![0x6c],
            Instruction::I32DivS => vec![0x6d],
            Instruction::I64Add => vec![0x7c],
            Instruction::I64Sub => vec![0x7d],
            Instruction::I64Mul => vec![0x7e],
            Instruction::I64DivS => vec![0x7f],
            Instruction::I64Eq => vec![0x51],
            Instruction::I64Ne => vec![0x52],
            Instruction::I64LtS => vec![0x53],
            Instruction::I64GtS => vec![0x54],
            Instruction::I32WrapI64 => vec![0xa7],
            _ => vec![],
        }
    }
}

impl BlockType {
    pub fn serialize(&self) -> Vec<u8> {
        match self {
            BlockType::Empty => vec![0x40],
            BlockType::Value(typ) => vec![typ.to_u8()],
        }
    }
}

impl ValType {
    pub fn to_u8(&self) -> u8 {
        match self {
            ValType::I32 => 0x7f,
            ValType::I64 => 0x7e,
            ValType::F32 => 0x7d,
            ValType::F64 => 0x7c,
        }
    }
}

impl FunctionType {
    pub fn new(params: Vec<ValType>, results: Vec<ValType>) -> Self {
        Self { params, results }
    }
    
    pub fn serialize(&self) -> Vec<u8> {
        let mut buf = vec![0x60];
        buf.push(self.params.len() as u8);
        for param in &self.params {
            buf.push(param.to_u8());
        }
        buf.push(self.results.len() as u8);
        for result in &self.results {
            buf.push(result.to_u8());
        }
        buf
    }
}

impl Import {
    pub fn serialize(&self) -> Vec<u8> {
        let mut buf = Vec::new();
        
        // Module name
        buf.extend_from_slice(&(self.module.len() as u32).to_le_bytes());
        buf.extend_from_slice(self.module.as_bytes());
        
        // Import name
        buf.extend_from_slice(&(self.name.len() as u32).to_le_bytes());
        buf.extend_from_slice(self.name.as_bytes());
        
        // Import kind
        match &self.kind {
            ImportKind::Function(func_type) => {
                buf.push(0x00);
                buf.extend_from_slice(&func_type.serialize());
            }
        }
        
        buf
    }
}

pub enum ImportKind {
    Function(FunctionType),
}

impl MemorySection {
    pub fn new(initial: u32, maximum: Option<u32>) -> Self {
        Self { initial, maximum }
    }
    
    pub fn serialize(&self) -> Vec<u8> {
        let mut buf = vec![0x01]; // 1 memory
        
        // Flags
        if self.maximum.is_some() {
            buf.push(0x01); // Has maximum
        } else {
            buf.push(0x00); // No maximum
        }
        
        // Initial pages
        buf.extend_from_slice(&self.initial.to_le_bytes());
        
        // Maximum pages
        if let Some(max) = self.maximum {
            buf.extend_from_slice(&max.to_le_bytes());
        }
        
        buf
    }
}

pub struct Function {
    pub type_index: u32,
    pub func_type: FunctionType,
    pub body: FunctionBody,
}

pub struct Export {
    pub name: String,
    pub kind: ExportKind,
    pub index: u32,
}

pub enum ExportKind {
    Function,
    Table,
    Memory,
    Global,
}

pub struct MemorySection {
    pub initial: u32,
    pub maximum: Option<u32>,
}

pub struct Import {
    pub module: String,
    pub name: String,
    pub kind: ImportKind,
}

pub struct FunctionType {
    pub params: Vec<ValType>,
    pub results: Vec<ValType>,
}
```

---

## 15.6 Security Model Comparison

### Comparação de Modelos de Segurança

```rust
// security-comparison/src/lib.rs
use std::collections::HashMap;

pub struct SecurityModelComparator {
    models: HashMap<String, SecurityModel>,
}

pub struct SecurityModel {
    name: String,
    features: Vec<SecurityFeature>,
    vulnerabilities: Vec<CommonVulnerability>,
    mitigations: Vec<Mitigation>,
    score: SecurityScore,
}

pub struct SecurityFeature {
    name: String,
    description: String,
    implementation: String,
    effectiveness: EffectivenessRating,
}

pub enum EffectivenessRating {
    High,
    Medium,
    Low,
    None,
}

pub struct CommonVulnerability {
    name: String,
    description: String,
    prevalence: Prevalence,
    impact: Impact,
    prevention: Vec<String>,
}

pub enum Prevalence {
    Common,
    Uncommon,
    Rare,
}

pub enum Impact {
    Critical,
    High,
    Medium,
    Low,
}

pub struct Mitigation {
    vulnerability: String,
    technique: String,
    effectiveness: f64,
}

pub struct SecurityScore {
    overall: f64,
    breakdown: HashMap<String, f64>,
}

impl SecurityModelComparator {
    pub fn new() -> Self {
        let mut comparator = Self {
            models: HashMap::new(),
        };
        
        comparator.add_evm_model();
        comparator.add_wasm_model();
        comparator.add_solana_model();
        
        comparator
    }
    
    fn add_evm_model(&mut self) {
        let model = SecurityModel {
            name: "EVM (Ethereum Virtual Machine)".to_string(),
            features: vec![
                SecurityFeature {
                    name: "Stack-based Execution".to_string(),
                    description: "Uses a stack machine for execution".to_string(),
                    implementation: "Stack machine with 1024 depth limit".to_string(),
                    effectiveness: EffectivenessRating::Medium,
                },
                SecurityFeature {
                    name: "Gas Metering".to_string(),
                    description: "Every operation costs gas".to_string(),
                    implementation: "Static gas costs per opcode".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Sandboxed Execution".to_string(),
                    description: "Contracts cannot access external state".to_string(),
                    implementation: "Isolated execution environment".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Deterministic Execution".to_string(),
                    description: "Same input always produces same output".to_string(),
                    implementation: "No external state or randomness".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
            ],
            vulnerabilities: vec![
                CommonVulnerability {
                    name: "Reentrancy".to_string(),
                    description: "External calls can re-enter contract".to_string(),
                    prevalence: Prevalence::Common,
                    impact: Impact::Critical,
                    prevention: vec![
                        "Checks-Effects-Interactions pattern".to_string(),
                        "Reentrancy guards".to_string(),
                    ],
                },
                CommonVulnerability {
                    name: "Integer Overflow".to_string(),
                    description: "Arithmetic operations can overflow".to_string(),
                    prevalence: Prevalence::Common,
                    impact: Impact::High,
                    prevention: vec![
                        "SafeMath library".to_string(),
                        "Solidity 0.8+ overflow checks".to_string(),
                    ],
                },
                CommonVulnerability {
                    name: "Front-running".to_string(),
                    description: "Transactions can be observed and front-run".to_string(),
                    prevalence: Prevalence::Uncommon,
                    impact: Impact::Medium,
                    prevention: vec![
                        "Commit-reveal schemes".to_string(),
                        "Flashbots".to_string(),
                    ],
                },
            ],
            mitigations: vec![
                Mitigation {
                    vulnerability: "Reentrancy".to_string(),
                    technique: "ReentrancyGuard".to_string(),
                    effectiveness: 0.95,
                },
                Mitigation {
                    vulnerability: "Integer Overflow".to_string(),
                    technique: "Solidity 0.8+ built-in checks".to_string(),
                    effectiveness: 0.99,
                },
            ],
            score: SecurityScore {
                overall: 0.75,
                breakdown: HashMap::from([
                    ("memory_safety".to_string(), 0.8),
                    ("type_safety".to_string(), 0.7),
                    ("resource_control".to_string(), 0.9),
                    ("determinism".to_string(), 1.0),
                ]),
            },
        };
        
        self.models.insert("evm".to_string(), model);
    }
    
    fn add_wasm_model(&mut self) {
        let model = SecurityModel {
            name: "WebAssembly".to_string(),
            features: vec![
                SecurityFeature {
                    name: "Memory Safety".to_string(),
                    description: "Linear memory with bounds checking".to_string(),
                    implementation: "Bounds-checked memory access".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Type Safety".to_string(),
                    description: "Strong static typing system".to_string(),
                    implementation: "Validation and type checking at load time".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Sandboxed Execution".to_string(),
                    description: "Cannot access host system directly".to_string(),
                    implementation: "Capability-based import system".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Stack Safety".to_string(),
                    description: "Separate call stack with overflow detection".to_string(),
                    implementation: "Fixed-size call stack".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
            ],
            vulnerabilities: vec![
                CommonVulnerability {
                    name: "Supply Chain Attacks".to_string(),
                    description: "Malicious dependencies".to_string(),
                    prevalence: Prevalence::Uncommon,
                    impact: Impact::High,
                    prevention: vec![
                        "Dependency auditing".to_string(),
                        "Reproducible builds".to_string(),
                    ],
                },
                CommonVulnerability {
                    name: "Side-channel Attacks".to_string(),
                    description: "Timing or cache-based attacks".to_string(),
                    prevalence: Prevalence::Rare,
                    impact: Impact::Medium,
                    prevention: vec![
                        "Constant-time implementations".to_string(),
                        "Memory access pattern obfuscation".to_string(),
                    ],
                },
            ],
            mitigations: vec![
                Mitigation {
                    vulnerability: "Memory Safety".to_string(),
                    technique: "Bounds checking".to_string(),
                    effectiveness: 0.99,
                },
                Mitigation {
                    vulnerability: "Type Safety".to_string(),
                    technique: "Static validation".to_string(),
                    effectiveness: 0.99,
                },
            ],
            score: SecurityScore {
                overall: 0.92,
                breakdown: HashMap::from([
                    ("memory_safety".to_string(), 0.98),
                    ("type_safety".to_string(), 0.95),
                    ("resource_control".to_string(), 0.90),
                    ("determinism".to_string(), 0.95),
                ]),
            },
        };
        
        self.models.insert("wasm".to_string(), model);
    }
    
    fn add_solana_model(&mut self) {
        let model = SecurityModel {
            name: "Solana (BPF/SBF)".to_string(),
            features: vec![
                SecurityFeature {
                    name: "Register-based VM".to_string(),
                    description: "Uses register-based virtual machine".to_string(),
                    implementation: "Berkeley Packet Filter Extended".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Compute Units".to_string(),
                    description: "Resource metering via compute units".to_string(),
                    implementation: "Dynamic compute unit costs".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
                SecurityFeature {
                    name: "Account Model".to_string(),
                    description: "Explicit account access control".to_string(),
                    implementation: "Account ownership and signer verification".to_string(),
                    effectiveness: EffectivenessRating::High,
                },
            ],
            vulnerabilities: vec![
                CommonVulnerability {
                    name: "Account Confusion".to_string(),
                    description: "Incorrect account validation".to_string(),
                    prevalence: Prevalence::Common,
                    impact: Impact::Critical,
                    prevention: vec![
                        "Strict account validation".to_string(),
                        "Anchor framework".to_string(),
                    ],
                },
            ],
            mitigations: vec![
                Mitigation {
                    vulnerability: "Account Confusion".to_string(),
                    technique: "Anchor constraints".to_string(),
                    effectiveness: 0.95,
                },
            ],
            score: SecurityScore {
                overall: 0.85,
                breakdown: HashMap::from([
                    ("memory_safety".to_string(), 0.90),
                    ("type_safety".to_string(), 0.85),
                    ("resource_control".to_string(), 0.88),
                    ("determinism".to_string(), 0.95),
                ]),
            },
        };
        
        self.models.insert("solana".to_string(), model);
    }
    
    pub fn compare(&self, model1: &str, model2: &str) -> ComparisonResult {
        let m1 = self.models.get(model1).unwrap();
        let m2 = self.models.get(model2).unwrap();
        
        let mut feature_comparison = Vec::new();
        
        for feature1 in &m1.features {
            let matching_feature = m2.features.iter().find(|f| f.name == feature1.name);
            
            feature_comparison.push(FeatureComparison {
                name: feature1.name.clone(),
                model1_effectiveness: feature1.effectiveness.clone(),
                model2_effectiveness: matching_feature
                    .map(|f| f.effectiveness.clone())
                    .unwrap_or(EffectivenessRating::None),
            });
        }
        
        let vulnerability_comparison = self.compare_vulnerabilities(&m1.vulnerabilities, &m2.vulnerabilities);
        
        ComparisonResult {
            model1_name: m1.name.clone(),
            model2_name: m2.name.clone(),
            feature_comparison,
            vulnerability_comparison,
            overall_comparison: ScoreComparison {
                model1_score: m1.score.overall,
                model2_score: m2.score.overall,
                winner: if m1.score.overall > m2.score.overall {
                    model1.to_string()
                } else if m2.score.overall > m1.score.overall {
                    model2.to_string()
                } else {
                    "tie".to_string()
                },
            },
        }
    }
    
    fn compare_vulnerabilities(
        &self,
        vulns1: &[CommonVulnerability],
        vulns2: &[CommonVulnerability],
    ) -> VulnerabilityComparison {
        let mut unique_to_model1 = Vec::new();
        let mut unique_to_model2 = Vec::new();
        let mut common = Vec::new();
        
        for vuln in vulns1 {
            if vulns2.iter().any(|v| v.name == vuln.name) {
                common.push(vuln.name.clone());
            } else {
                unique_to_model1.push(vuln.name.clone());
            }
        }
        
        for vuln in vulns2 {
            if !vulns1.iter().any(|v| v.name == vuln.name) {
                unique_to_model2.push(vuln.name.clone());
            }
        }
        
        VulnerabilityComparison {
            unique_to_model1,
            unique_to_model2,
            common,
        }
    }
    
    pub fn generate_report(&self) -> String {
        let mut report = String::new();
        
        report.push_str("# Security Model Comparison Report\n\n");
        
        for (name, model) in &self.models {
            report.push_str(&format!("## {}\n\n", model.name));
            report.push_str(&format!("Overall Score: {:.2}\n\n", model.score.overall));
            
            report.push_str("### Security Features\n\n");
            for feature in &model.features {
                report.push_str(&format!(
                    "- **{}**: {} ({:?})\n",
                    feature.name, feature.description, feature.effectiveness
                ));
            }
            
            report.push_str("\n### Common Vulnerabilities\n\n");
            for vuln in &model.vulnerabilities {
                report.push_str(&format!(
                    "- **{}**: {} (Prevalence: {:?}, Impact: {:?})\n",
                    vuln.name, vuln.description, vuln.prevalence, vuln.impact
                ));
            }
            
            report.push_str("\n### Security Score Breakdown\n\n");
            for (category, score) in &model.score.breakdown {
                report.push_str(&format!("- {}: {:.2}\n", category, score));
            }
            
            report.push_str("\n");
        }
        
        report
    }
}

pub struct ComparisonResult {
    pub model1_name: String,
    pub model2_name: String,
    pub feature_comparison: Vec<FeatureComparison>,
    pub vulnerability_comparison: VulnerabilityComparison,
    pub overall_comparison: ScoreComparison,
}

pub struct FeatureComparison {
    pub name: String,
    pub model1_effectiveness: EffectivenessRating,
    pub model2_effectiveness: EffectivenessRating,
}

pub struct VulnerabilityComparison {
    pub unique_to_model1: Vec<String>,
    pub unique_to_model2: Vec<String>,
    pub common: Vec<String>,
}

pub struct ScoreComparison {
    pub model1_score: f64,
    pub model2_score: f64,
    pub winner: String,
}
```

---

## 15.7 Gas Metering

### Sistema de Medição de Gas

```rust
// gas-metering/src/lib.rs
use std::collections::HashMap;

pub struct GasMeter {
    config: GasConfig,
    operations: HashMap<String, OperationCost>,
    current_gas: u64,
    max_gas: u64,
    log: Vec<GasEntry>,
}

pub struct GasConfig {
    pub base_cost: u64,
    pub memory_cost_per_byte: u64,
    pub storage_cost_per_byte: u64,
    pub computation_cost_per_instruction: u64,
    pub external_call_cost: u64,
    pub max_gas_per_transaction: u64,
}

pub struct OperationCost {
    pub name: String,
    pub base_cost: u64,
    pub variable_cost: Option<VariableCost>,
}

pub enum VariableCost {
    PerByte(u64),
    PerInstruction(u64),
    PerSlot(u64),
}

pub struct GasEntry {
    pub operation: String,
    pub cost: u64,
    pub timestamp: u64,
    pub cumulative: u64,
}

pub struct GasReceipt {
    pub total_gas_used: u64,
    pub gas_limit: u64,
    pub gas_remaining: u64,
    pub operations: Vec<GasEntry>,
    pub refund: u64,
}

impl GasMeter {
    pub fn new(config: GasConfig) -> Self {
        let mut operations = HashMap::new();
        
        // Add default operation costs
        operations.insert(
            "i32.add".to_string(),
            OperationCost {
                name: "i32.add".to_string(),
                base_cost: 3,
                variable_cost: None,
            },
        );
        
        operations.insert(
            "i64.add".to_string(),
            OperationCost {
                name: "i64.add".to_string(),
                base_cost: 3,
                variable_cost: None,
            },
        );
        
        operations.insert(
            "memory.grow".to_string(),
            OperationCost {
                name: "memory.grow".to_string(),
                base_cost: 1000,
                variable_cost: Some(VariableCost::PerByte(10)),
            },
        );
        
        operations.insert(
            "storage.write".to_string(),
            OperationCost {
                name: "storage.write".to_string(),
                base_cost: 5000,
                variable_cost: Some(VariableCost::PerByte(100)),
            },
        );
        
        operations.insert(
            "storage.read".to_string(),
            OperationCost {
                name: "storage.read".to_string(),
                base_cost: 2000,
                variable_cost: Some(VariableCost::PerByte(10)),
            },
        );
        
        operations.insert(
            "external_call".to_string(),
            OperationCost {
                name: "external_call".to_string(),
                base_cost: 10000,
                variable_cost: None,
            },
        );
        
        operations.insert(
            "event.log".to_string(),
            OperationCost {
                name: "event.log".to_string(),
                base_cost: 3000,
                variable_cost: Some(VariableCost::PerByte(50)),
            },
        );
        
        Self {
            config,
            operations,
            current_gas: 0,
            max_gas: config.max_gas_per_transaction,
            log: Vec::new(),
        }
    }
    
    pub fn consume(&mut self, operation: &str, units: Option<u64>) -> Result<u64, GasError> {
        let cost = self.calculate_cost(operation, units)?;
        
        if self.current_gas + cost > self.max_gas {
            return Err(GasError::InsufficientGas {
                required: cost,
                available: self.max_gas - self.current_gas,
            });
        }
        
        self.current_gas += cost;
        
        self.log.push(GasEntry {
            operation: operation.to_string(),
            cost,
            timestamp: self.get_timestamp(),
            cumulative: self.current_gas,
        });
        
        Ok(cost)
    }
    
    pub fn calculate_cost(&self, operation: &str, units: Option<u64>) -> Result<u64, GasError> {
        let op_cost = self
            .operations
            .get(operation)
            .ok_or_else(|| GasError::UnknownOperation(operation.to_string()))?;
        
        let mut cost = op_cost.base_cost;
        
        if let Some(variable_cost) = &op_cost.variable_cost {
            if let Some(units) = units {
                match variable_cost {
                    VariableCost::PerByte(rate) => {
                        cost += units * rate;
                    }
                    VariableCost::PerInstruction(rate) => {
                        cost += units * rate;
                    }
                    VariableCost::PerSlot(rate) => {
                        cost += units * rate;
                    }
                }
            }
        }
        
        Ok(cost)
    }
    
    pub fn get_receipt(&self) -> GasReceipt {
        let refund = self.calculate_refund();
        
        GasReceipt {
            total_gas_used: self.current_gas,
            gas_limit: self.max_gas,
            gas_remaining: self.max_gas - self.current_gas,
            operations: self.log.clone(),
            refund,
        }
    }
    
    fn calculate_refund(&self) -> u64 {
        // Calculate refund for storage clears
        let mut refund = 0;
        
        for entry in &self.log {
            if entry.operation == "storage.clear" {
                refund += entry.cost / 2; // 50% refund for clears
            }
        }
        
        // Cap refund at 20% of gas used
        let max_refund = self.current_gas / 5;
        refund.min(max_refund)
    }
    
    pub fn remaining(&self) -> u64 {
        self.max_gas - self.current_gas
    }
    
    pub fn is_empty(&self) -> bool {
        self.current_gas >= self.max_gas
    }
    
    fn get_timestamp(&self) -> u64 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos() as u64
    }
}

pub enum GasError {
    InsufficientGas { required: u64, available: u64 },
    UnknownOperation(String),
    Overflow,
}

impl std::fmt::Display for GasError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::InsufficientGas { required, available } => {
                write!(f, "Insufficient gas: {} required, {} available", required, available)
            }
            Self::UnknownOperation(op) => write!(f, "Unknown operation: {}", op),
            Self::Overflow => write!(f, "Gas calculation overflow"),
        }
    }
}

pub struct WasmGasInstrumenter {
    gas_meter: GasMeter,
    instruction_costs: HashMap<u8, u64>,
}

impl WasmGasInstrumenter {
    pub fn new(config: GasConfig) -> Self {
        let mut instruction_costs = HashMap::new();
        
        // Wasm instruction costs
        instruction_costs.insert(0x01, 1);  // nop
        instruction_costs.insert(0x02, 1);  // block
        instruction_costs.insert(0x03, 1);  // loop
        instruction_costs.insert(0x04, 1);  // if
        instruction_costs.insert(0x05, 1);  // else
        instruction_costs.insert(0x0b, 1);  // end
        instruction_costs.insert(0x0c, 1);  // br
        instruction_costs.insert(0x0d, 1);  // br_if
        instruction_costs.insert(0x0f, 1);  // return
        instruction_costs.insert(0x10, 10); // call
        instruction_costs.insert(0x11, 10); // call_indirect
        instruction_costs.insert(0x20, 1);  // local.get
        instruction_costs.insert(0x21, 1);  // local.set
        instruction_costs.insert(0x22, 1);  // local.tee
        instruction_costs.insert(0x23, 1);  // global.get
        instruction_costs.insert(0x24, 1);  // global.set
        instruction_costs.insert(0x28, 5);  // i32.load
        instruction_costs.insert(0x29, 5);  // i64.load
        instruction_costs.insert(0x36, 10); // i32.store
        instruction_costs.insert(0x37, 10); // i64.store
        instruction_costs.insert(0x39, 100); // memory.grow
        instruction_costs.insert(0x3f, 1);  // memory.size
        instruction_costs.insert(0x41, 1);  // i32.const
        instruction_costs.insert(0x42, 1);  // i64.const
        instruction_costs.insert(0x6a, 3);  // i32.add
        instruction_costs.insert(0x6b, 3);  // i32.sub
        instruction_costs.insert(0x6c, 5);  // i32.mul
        instruction_costs.insert(0x6d, 5);  // i32.div_s
        instruction_costs.insert(0x7c, 3);  // i64.add
        instruction_costs.insert(0x7d, 3);  // i64.sub
        instruction_costs.insert(0x7e, 5);  // i64.mul
        instruction_costs.insert(0x7f, 5);  // i64.div_s
        
        Self {
            gas_meter: GasMeter::new(config),
            instruction_costs,
        }
    }
    
    pub fn instrument_bytecode(&self, bytecode: &[u8]) -> Result<Vec<u8>, GasError> {
        let mut instrumented = Vec::new();
        
        // Parse and instrument WASM bytecode
        let mut i = 0;
        while i < bytecode.len() {
            let opcode = bytecode[i];
            
            // Add gas consumption instruction
            if let Some(cost) = self.instruction_costs.get(&opcode) {
                // In practice, would inject gas counter check
                instrumented.push(opcode);
            } else {
                instrumented.push(opcode);
            }
            
            i += 1;
            
            // Skip instruction operands
            match opcode {
                0x02 | 0x03 | 0x04 => {
                    // Block, loop, if - skip block type
                    i += 1;
                }
                0x0c | 0x0d => {
                    // br, br_if - skip label index
                    i += 1;
                }
                0x10 => {
                    // call - skip function index
                    i += 1;
                }
                0x20 | 0x21 | 0x22 => {
                    // local.get/set/tee - skip local index
                    i += 1;
                }
                0x28 | 0x29 | 0x2a | 0x2b | 0x2c | 0x2d | 0x2e | 0x2f
                | 0x30 | 0x31 | 0x32 | 0x33 | 0x34 | 0x35 | 0x36 | 0x37 => {
                    // Memory instructions - skip offset
                    i += 4;
                }
                0x41 => {
                    // i32.const - skip 4 bytes
                    i += 4;
                }
                0x42 => {
                    // i64.const - skip 8 bytes
                    i += 8;
                }
                _ => {}
            }
        }
        
        Ok(instrumented)
    }
    
    pub fn consume_instruction(&mut self, opcode: u8) -> Result<u64, GasError> {
        let cost = self
            .instruction_costs
            .get(&opcode)
            .copied()
            .unwrap_or(1);
        
        self.gas_meter.consume(&format!("opcode_{}", opcode), Some(cost))
    }
    
    pub fn consume_memory_grow(&mut self, pages: u32) -> Result<u64, GasError> {
        self.gas_meter
            .consume("memory.grow", Some(pages as u64 * 65536))
    }
    
    pub fn consume_storage_write(&mut self, bytes: u64) -> Result<u64, GasError> {
        self.gas_meter.consume("storage.write", Some(bytes))
    }
    
    pub fn consume_storage_read(&mut self, bytes: u64) -> Result<u64, GasError> {
        self.gas_meter.consume("storage.read", Some(bytes))
    }
    
    pub fn consume_external_call(&mut self) -> Result<u64, GasError> {
        self.gas_meter.consume("external_call", None)
    }
    
    pub fn get_receipt(&self) -> GasReceipt {
        self.gas_meter.get_receipt()
    }
    
    pub fn remaining(&self) -> u64 {
        self.gas_meter.remaining()
    }
}

pub struct GasConfigBuilder {
    config: GasConfig,
}

impl GasConfigBuilder {
    pub fn new() -> Self {
        Self {
            config: GasConfig {
                base_cost: 1,
                memory_cost_per_byte: 1,
                storage_cost_per_byte: 100,
                computation_cost_per_instruction: 1,
                external_call_cost: 1000,
                max_gas_per_transaction: 30_000_000,
            },
        }
    }
    
    pub fn base_cost(mut self, cost: u64) -> Self {
        self.config.base_cost = cost;
        self
    }
    
    pub fn memory_cost_per_byte(mut self, cost: u64) -> Self {
        self.config.memory_cost_per_byte = cost;
        self
    }
    
    pub fn storage_cost_per_byte(mut self, cost: u64) -> Self {
        self.config.storage_cost_per_byte = cost;
        self
    }
    
    pub fn computation_cost_per_instruction(mut self, cost: u64) -> Self {
        self.config.computation_cost_per_instruction = cost;
        self
    }
    
    pub fn external_call_cost(mut self, cost: u64) -> Self {
        self.config.external_call_cost = cost;
        self
    }
    
    pub fn max_gas_per_transaction(mut self, max: u64) -> Self {
        self.config.max_gas_per_transaction = max;
        self
    }
    
    pub fn build(self) -> GasConfig {
        self.config
    }
}
```

---

## 15.8 Deterministic Execution

### Garantia de Execução Determinística

```rust
// deterministic-execution/src/lib.rs
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct DeterministicExecutor {
    state: ExecutionState,
    config: DeterministicConfig,
    rng: DeterministicRNG,
    time_provider: TimeProvider,
}

pub struct ExecutionState {
    pub stack: Vec<Value>,
    pub locals: Vec<Value>,
    pub memory: Vec<u8>,
    pub storage: HashMap<Vec<u8>, Vec<u8>>,
    pub balance: u128,
    pub gas_remaining: u64,
}

pub struct DeterministicConfig {
    pub max_stack_depth: usize,
    pub max_memory_pages: u32,
    pub max_locals: usize,
    pub max_instruction_count: u64,
    pub enable_debug: bool,
}

pub enum Value {
    I32(i32),
    I64(i64),
    F32(f32),
    F64(f64),
}

pub struct DeterministicRNG {
    seed: u64,
    state: u64,
}

impl DeterministicRNG {
    pub fn new(seed: u64) -> Self {
        Self {
            seed,
            state: seed,
        }
    }
    
    pub fn next(&mut self) -> u64 {
        // Mulberry32 PRNG
        self.state = self.state.wrapping_add(0x6D2B79F5);
        let mut z = self.state;
        z = (z ^ (z >> 15)) & 0xFFFFFFFF;
        z = z.wrapping_mul(0x1B873593);
        z = z ^ (z >> 13);
        z = z & 0xFFFFFFFF;
        z = z.wrapping_mul(0x1B56C4E9);
        z ^ (z >> 16)
    }
    
    pub fn fill_bytes(&mut self, buf: &mut [u8]) {
        for chunk in buf.chunks_mut(8) {
            let rand = self.next();
            let bytes = rand.to_le_bytes();
            for (i, byte) in chunk.iter_mut().enumerate() {
                *byte = bytes[i];
            }
        }
    }
}

pub struct TimeProvider {
    base_time: u64,
    deterministic: bool,
}

impl TimeProvider {
    pub fn new(deterministic: bool) -> Self {
        Self {
            base_time: 1000000, // Fixed time for determinism
            deterministic,
        }
    }
    
    pub fn now(&self) -> u64 {
        if self.deterministic {
            self.base_time
        } else {
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs()
        }
    }
}

impl DeterministicExecutor {
    pub fn new(config: DeterministicConfig, seed: u64) -> Self {
        Self {
            state: ExecutionState {
                stack: Vec::with_capacity(config.max_stack_depth),
                locals: Vec::with_capacity(config.max_locals),
                memory: vec![0; config.max_memory_pages as usize * 65536],
                storage: HashMap::new(),
                balance: 0,
                gas_remaining: u64::MAX,
            },
            config,
            rng: DeterministicRNG::new(seed),
            time_provider: TimeProvider::new(true),
        }
    }
    
    pub fn execute(
        &mut self,
        bytecode: &[u8],
        input: &[u8],
        gas_limit: u64,
    ) -> Result<ExecutionResult, ExecutionError> {
        self.state.gas_remaining = gas_limit;
        
        let mut instruction_count = 0;
        let mut pc = 0;
        
        while pc < bytecode.len() {
            if instruction_count >= self.config.max_instruction_count {
                return Err(ExecutionError::InstructionLimitExceeded);
            }
            
            if self.state.gas_remaining == 0 {
                return Err(ExecutionError::OutOfGas);
            }
            
            let opcode = bytecode[pc];
            pc += 1;
            
            // Consume gas for each instruction
            self.state.gas_remaining -= 1;
            
            match opcode {
                0x01 => {} // nop
                0x0b => {} // end
                0x20 => {
                    // local.get
                    let index = bytecode[pc] as usize;
                    pc += 1;
                    
                    if index >= self.state.locals.len() {
                        return Err(ExecutionError::InvalidLocalIndex(index));
                    }
                    
                    self.state.stack.push(self.state.locals[index].clone());
                }
                0x21 => {
                    // local.set
                    let index = bytecode[pc] as usize;
                    pc += 1;
                    
                    if index >= self.state.locals.len() {
                        return Err(ExecutionError::InvalidLocalIndex(index));
                    }
                    
                    let value = self.state.stack.pop().ok_or(ExecutionError::StackUnderflow)?;
                    self.state.locals[index] = value;
                }
                0x41 => {
                    // i32.const
                    let value = i32::from_le_bytes([
                        bytecode[pc],
                        bytecode[pc + 1],
                        bytecode[pc + 2],
                        bytecode[pc + 3],
                    ]);
                    pc += 4;
                    
                    self.state.stack.push(Value::I32(value));
                }
                0x42 => {
                    // i64.const
                    let value = i64::from_le_bytes([
                        bytecode[pc],
                        bytecode[pc + 1],
                        bytecode[pc + 2],
                        bytecode[pc + 3],
                        bytecode[pc + 4],
                        bytecode[pc + 5],
                        bytecode[pc + 6],
                        bytecode[pc + 7],
                    ]);
                    pc += 8;
                    
                    self.state.stack.push(Value::I64(value));
                }
                0x6a => {
                    // i32.add
                    let b = self.pop_i32()?;
                    let a = self.pop_i32()?;
                    self.state.stack.push(Value::I32(a.wrapping_add(b)));
                }
                0x6b => {
                    // i32.sub
                    let b = self.pop_i32()?;
                    let a = self.pop_i32()?;
                    self.state.stack.push(Value::I32(a.wrapping_sub(b)));
                }
                0x6c => {
                    // i32.mul
                    let b = self.pop_i32()?;
                    let a = self.pop_i32()?;
                    self.state.stack.push(Value::I32(a.wrapping_mul(b)));
                }
                0x7c => {
                    // i64.add
                    let b = self.pop_i64()?;
                    let a = self.pop_i64()?;
                    self.state.stack.push(Value::I64(a.wrapping_add(b)));
                }
                0x7d => {
                    // i64.sub
                    let b = self.pop_i64()?;
                    let a = self.pop_i64()?;
                    self.state.stack.push(Value::I64(a.wrapping_sub(b)));
                }
                0x7e => {
                    // i64.mul
                    let b = self.pop_i64()?;
                    let a = self.pop_i64()?;
                    self.state.stack.push(Value::I64(a.wrapping_mul(b)));
                }
                0x36 => {
                    // i32.store
                    let _align = bytecode[pc];
                    let _offset = u32::from_le_bytes([
                        bytecode[pc + 1],
                        bytecode[pc + 2],
                        bytecode[pc + 3],
                        bytecode[pc + 4],
                    ]);
                    pc += 5;
                    
                    let value = self.pop_i32()?;
                    let address = self.pop_i32()? as usize;
                    
                    if address + 4 > self.state.memory.len() {
                        return Err(ExecutionError::MemoryAccessViolation);
                    }
                    
                    self.state.memory[address..address + 4]
                        .copy_from_slice(&value.to_le_bytes());
                }
                0x28 => {
                    // i32.load
                    let _align = bytecode[pc];
                    let _offset = u32::from_le_bytes([
                        bytecode[pc + 1],
                        bytecode[pc + 2],
                        bytecode[pc + 3],
                        bytecode[pc + 4],
                    ]);
                    pc += 5;
                    
                    let address = self.pop_i32()? as usize;
                    
                    if address + 4 > self.state.memory.len() {
                        return Err(ExecutionError::MemoryAccessViolation);
                    }
                    
                    let value = i32::from_le_bytes([
                        self.state.memory[address],
                        self.state.memory[address + 1],
                        self.state.memory[address + 2],
                        self.state.memory[address + 3],
                    ]);
                    
                    self.state.stack.push(Value::I32(value));
                }
                0x39 => {
                    // memory.grow
                    let pages = self.pop_i32()? as u32;
                    
                    let current_pages = self.state.memory.len() / 65536;
                    let new_pages = current_pages + pages;
                    
                    if new_pages > self.config.max_memory_pages {
                        self.state.stack.push(Value::I32(-1));
                    } else {
                        self.state.memory.resize(new_pages as usize * 65536, 0);
                        self.state.stack.push(Value::I32(current_pages as i32));
                    }
                }
                0x3f => {
                    // memory.size
                    let pages = self.state.memory.len() / 65536;
                    self.state.stack.push(Value::I32(pages as i32));
                }
                0x00 => {
                    // unreachable
                    return Err(ExecutionError::Unreachable);
                }
                0x0c => {
                    // br
                    let _label = bytecode[pc];
                    pc += 1;
                    // In real implementation, would handle branching
                }
                0x0d => {
                    // br_if
                    let _label = bytecode[pc];
                    pc += 1;
                    let condition = self.pop_i32()?;
                    if condition != 0 {
                        // Would handle branching
                    }
                }
                0x10 => {
                    // call
                    let _function_index = bytecode[pc];
                    pc += 1;
                    // In real implementation, would handle function calls
                }
                _ => {
                    return Err(ExecutionError::UnknownInstruction(opcode));
                }
            }
            
            instruction_count += 1;
        }
        
        Ok(ExecutionResult {
            output: self.get_output(),
            gas_used: gas_limit - self.state.gas_remaining,
            storage: self.state.storage.clone(),
            events: vec![],
        })
    }
    
    fn pop_i32(&mut self) -> Result<i32, ExecutionError> {
        match self.state.stack.pop() {
            Some(Value::I32(v)) => Ok(v),
            Some(_) => Err(ExecutionError::TypeMismatch),
            None => Err(ExecutionError::StackUnderflow),
        }
    }
    
    fn pop_i64(&mut self) -> Result<i64, ExecutionError> {
        match self.state.stack.pop() {
            Some(Value::I64(v)) => Ok(v),
            Some(_) => Err(ExecutionError::TypeMismatch),
            None => Err(ExecutionError::StackUnderflow),
        }
    }
    
    fn get_output(&self) -> Vec<u8> {
        // Extract output from memory
        vec![]
    }
}

pub struct ExecutionResult {
    pub output: Vec<u8>,
    pub gas_used: u64,
    pub storage: HashMap<Vec<u8>, Vec<u8>>,
    pub events: Vec<Event>,
}

pub struct Event {
    pub topics: Vec<Vec<u8>>,
    pub data: Vec<u8>,
}

pub enum ExecutionError {
    OutOfGas,
    InstructionLimitExceeded,
    StackOverflow,
    StackUnderflow,
    TypeMismatch,
    InvalidLocalIndex(usize),
    MemoryAccessViolation,
    Unreachable,
    UnknownInstruction(u8),
}

impl std::fmt::Display for ExecutionError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::OutOfGas => write!(f, "Out of gas"),
            Self::InstructionLimitExceeded => write!(f, "Instruction limit exceeded"),
            Self::StackOverflow => write!(f, "Stack overflow"),
            Self::StackUnderflow => write!(f, "Stack underflow"),
            Self::TypeMismatch => write!(f, "Type mismatch"),
            Self::InvalidLocalIndex(idx) => write!(f, "Invalid local index: {}", idx),
            Self::MemoryAccessViolation => write!(f, "Memory access violation"),
            Self::Unreachable => write!(f, "Unreachable instruction executed"),
            Self::UnknownInstruction(op) => write!(f, "Unknown instruction: 0x{:02x}", op),
        }
    }
}

pub struct DeterminismVerifier {
    executor: DeterministicExecutor,
}

impl DeterminismVerifier {
    pub fn new(config: DeterministicConfig) -> Self {
        Self {
            executor: DeterministicExecutor::new(config, 12345), // Fixed seed
        }
    }
    
    pub fn verify_determinism(
        &mut self,
        bytecode: &[u8],
        input: &[u8],
        iterations: usize,
    ) -> DeterminismResult {
        let mut results = Vec::new();
        
        for i in 0..iterations {
            // Create fresh executor with same seed
            let mut executor = DeterministicExecutor::new(
                self.executor.config.clone(),
                12345, // Same seed
            );
            
            match executor.execute(bytecode, input, u64::MAX) {
                Ok(result) => {
                    results.push(Some(result));
                }
                Err(e) => {
                    results.push(None);
                    eprintln!("Iteration {} failed: {}", i, e);
                }
            }
        }
        
        // Check all results are identical
        let first_result = &results[0];
        let all_same = results.iter().all(|r| {
            match (first_result, r) {
                (Some(a), Some(b)) => a.output == b.output && a.gas_used == b.gas_used,
                (None, None) => true,
                _ => false,
            }
        });
        
        DeterminismResult {
            deterministic: all_same,
            iterations,
            first_result: first_result.clone(),
        }
    }
}

pub struct DeterminismResult {
    pub deterministic: bool,
    pub iterations: usize,
    pub first_result: Option<ExecutionResult>,
}
```

---

## 15.9 Audit Tools

### Ferramentas de Auditoria para Smart Contracts WASM

```rust
// audit-tools/src/lib.rs
use std::collections::HashMap;

pub struct WasmAuditor {
    rules: Vec<AuditRule>,
    analyzers: Vec<Box<dyn Analyzer>>,
    report_generator: ReportGenerator,
}

pub struct AuditRule {
    pub id: String,
    pub name: String,
    pub description: String,
    pub severity: Severity,
    pub category: RuleCategory,
    pub pattern: Pattern,
    pub recommendation: String,
}

pub enum Severity {
    Critical,
    High,
    Medium,
    Low,
    Informational,
}

pub enum RuleCategory {
    Security,
    Performance,
    Correctness,
    GasOptimization,
    BestPractice,
}

pub enum Pattern {
    OpcodePattern(Vec<u8>),
    FunctionPattern(String),
    ImportPattern(String),
    Custom(Box<dyn Fn(&WasmModule) -> bool>),
}

pub struct AuditFinding {
    pub rule_id: String,
    pub severity: Severity,
    pub location: Location,
    pub description: String,
    pub evidence: String,
    pub recommendation: String,
}

pub struct Location {
    pub offset: usize,
    pub function: Option<String>,
    pub line: Option<usize>,
}

pub struct AuditReport {
    pub findings: Vec<AuditFinding>,
    pub summary: AuditSummary,
    pub recommendations: Vec<String>,
}

pub struct AuditSummary {
    pub total_findings: usize,
    pub critical: usize,
    pub high: usize,
    pub medium: usize,
    pub low: usize,
    pub informational: usize,
    pub risk_score: f64,
}

pub trait Analyzer {
    fn analyze(&self, module: &WasmModule) -> Vec<AuditFinding>;
    fn name(&self) -> &str;
}

pub struct SecurityAnalyzer;
pub struct GasAnalyzer;
pub struct PerformanceAnalyzer;
pub struct CorrectnessAnalyzer;

impl Analyzer for SecurityAnalyzer {
    fn analyze(&self, module: &WasmModule) -> Vec<AuditFinding> {
        let mut findings = Vec::new();
        
        // Check for dangerous imports
        for import in &module.imports {
            if self.is_dangerous_import(&import.name) {
                findings.push(AuditFinding {
                    rule_id: "SEC001".to_string(),
                    severity: Severity::High,
                    location: Location {
                        offset: 0,
                        function: None,
                        line: None,
                    },
                    description: format!("Dangerous import detected: {}", import.name),
                    evidence: format!("Import: {}.{}", import.module, import.name),
                    recommendation: "Review if this import is necessary and properly secured".to_string(),
                });
            }
        }
        
        // Check for unchecked memory operations
        for (i, instruction) in module.code.iter().enumerate() {
            if self.is_unchecked_memory_op(instruction) {
                findings.push(AuditFinding {
                    rule_id: "SEC002".to_string(),
                    severity: Severity::Medium,
                    location: Location {
                        offset: i,
                        function: None,
                        line: None,
                    },
                    description: "Unchecked memory operation".to_string(),
                    evidence: format!("Instruction at offset {}", i),
                    recommendation: "Add bounds checking for memory operations".to_string(),
                });
            }
        }
        
        findings
    }
    
    fn name(&self) -> &str {
        "Security Analyzer"
    }
}

impl SecurityAnalyzer {
    fn is_dangerous_import(&self, name: &str) -> bool {
        matches!(
            name,
            "eval" | "exec" | "spawn" | "system" | "popen" | "dlopen"
        )
    }
    
    fn is_unchecked_memory_op(&self, instruction: &Instruction) -> bool {
        matches!(
            instruction,
            Instruction::MemoryLoad { .. } | Instruction::MemoryStore { .. }
        )
    }
}

impl Analyzer for GasAnalyzer {
    fn analyze(&self, module: &WasmModule) -> Vec<AuditFinding> {
        let mut findings = Vec::new();
        
        // Analyze gas consumption patterns
        let gas_usage = self.analyze_gas_usage(module);
        
        for (function_name, gas) in &gas_usage {
            if *gas > 1_000_000 {
                findings.push(AuditFinding {
                    rule_id: "GAS001".to_string(),
                    severity: Severity::Medium,
                    location: Location {
                        offset: 0,
                        function: Some(function_name.clone()),
                        line: None,
                    },
                    description: format!("High gas usage in function: {}", gas),
                    evidence: format!("Function {} uses {} gas units", function_name, gas),
                    recommendation: "Optimize function to reduce gas consumption".to_string(),
                });
            }
        }
        
        // Check for loops without gas limits
        for (i, instruction) in module.code.iter().enumerate() {
            if let Instruction::Loop { .. } = instruction {
                if !self.has_gas_check_in_loop(module, i) {
                    findings.push(AuditFinding {
                        rule_id: "GAS002".to_string(),
                        severity: Severity::High,
                        location: Location {
                            offset: i,
                            function: None,
                            line: None,
                        },
                        description: "Loop without gas limit check".to_string(),
                        evidence: format!("Loop at offset {}", i),
                        recommendation: "Add gas consumption check inside loop".to_string(),
                    });
                }
            }
        }
        
        findings
    }
    
    fn name(&self) -> &str {
        "Gas Analyzer"
    }
}

impl GasAnalyzer {
    fn analyze_gas_usage(&self, module: &WasmModule) -> HashMap<String, u64> {
        let mut usage = HashMap::new();
        
        for function in &module.functions {
            let gas = self.calculate_function_gas(function);
            usage.insert(function.name.clone(), gas);
        }
        
        usage
    }
    
    fn calculate_function_gas(&self, function: &FunctionDef) -> u64 {
        let mut gas = 0;
        
        for instruction in &function.code {
            gas += self.instruction_gas_cost(instruction);
        }
        
        gas
    }
    
    fn instruction_gas_cost(&self, instruction: &Instruction) -> u64 {
        match instruction {
            Instruction::Nop => 1,
            Instruction::Block { .. } => 1,
            Instruction::Loop { .. } => 1,
            Instruction::If { .. } => 1,
            Instruction::Else => 1,
            Instruction::End => 1,
            Instruction::Br { .. } => 1,
            Instruction::BrIf { .. } => 1,
            Instruction::Return => 1,
            Instruction::Call { .. } => 10,
            Instruction::LocalGet { .. } => 1,
            Instruction::LocalSet { .. } => 1,
            Instruction::LocalTee { .. } => 1,
            Instruction::I32Const { .. } => 1,
            Instruction::I64Const { .. } => 1,
            Instruction::I32Add => 3,
            Instruction::I32Sub => 3,
            Instruction::I32Mul => 5,
            Instruction::I32DivS => 5,
            Instruction::I64Add => 3,
            Instruction::I64Sub => 3,
            Instruction::I64Mul => 5,
            Instruction::I64DivS => 5,
            Instruction::MemoryLoad { .. } => 5,
            Instruction::MemoryStore { .. } => 10,
            Instruction::MemoryGrow { .. } => 1000,
            Instruction::MemorySize => 1,
            _ => 1,
        }
    }
    
    fn has_gas_check_in_loop(&self, module: &WasmModule, loop_offset: usize) -> bool {
        // Check if there's a gas check inside the loop
        // This is a simplified check
        false
    }
}

impl Analyzer for PerformanceAnalyzer {
    fn analyze(&self, module: &WasmModule) -> Vec<AuditFinding> {
        let mut findings = Vec::new();
        
        // Check for inefficient patterns
        for (i, instruction) in module.code.iter().enumerate() {
            if self.is_inefficient_pattern(instruction, &module.code, i) {
                findings.push(AuditFinding {
                    rule_id: "PERF001".to_string(),
                    severity: Severity::Low,
                    location: Location {
                        offset: i,
                        function: None,
                        line: None,
                    },
                    description: "Inefficient code pattern detected".to_string(),
                    evidence: format!("Pattern at offset {}", i),
                    recommendation: "Optimize code pattern for better performance".to_string(),
                });
            }
        }
        
        findings
    }
    
    fn name(&self) -> &str {
        "Performance Analyzer"
    }
}

impl PerformanceAnalyzer {
    fn is_inefficient_pattern(&self, instruction: &Instruction, code: &[Instruction], offset: usize) -> bool {
        // Check for redundant operations
        if offset > 0 {
            if let (Instruction::I32Const { value: 0 }, Instruction::I32Add) =
                (&code[offset - 1], instruction)
            {
                return true; // Adding zero is redundant
            }
        }
        
        false
    }
}

impl Analyzer for CorrectnessAnalyzer {
    fn analyze(&self, module: &WasmModule) -> Vec<AuditFinding> {
        let mut findings = Vec::new();
        
        // Check for type mismatches
        // Check for stack underflow/overflow
        // Check for unreachable code
        
        findings
    }
    
    fn name(&self) -> &str {
        "Correctness Analyzer"
    }
}

impl WasmAuditor {
    pub fn new() -> Self {
        let mut analyzers: Vec<Box<dyn Analyzer>> = Vec::new();
        analyzers.push(Box::new(SecurityAnalyzer));
        analyzers.push(Box::new(GasAnalyzer));
        analyzers.push(Box::new(PerformanceAnalyzer));
        analyzers.push(Box::new(CorrectnessAnalyzer));
        
        Self {
            rules: Self::default_rules(),
            analyzers,
            report_generator: ReportGenerator::new(),
        }
    }
    
    fn default_rules() -> Vec<AuditRule> {
        vec![
            AuditRule {
                id: "SEC001".to_string(),
                name: "Dangerous Import".to_string(),
                description: "Import of dangerous host function".to_string(),
                severity: Severity::High,
                category: RuleCategory::Security,
                pattern: Pattern::ImportPattern("eval".to_string()),
                recommendation: "Remove or restrict dangerous imports".to_string(),
            },
            AuditRule {
                id: "SEC002".to_string(),
                name: "Unchecked Memory".to_string(),
                description: "Memory operation without bounds checking".to_string(),
                severity: Severity::Medium,
                category: RuleCategory::Security,
                pattern: Pattern::OpcodePattern(vec![0x28, 0x36]),
                recommendation: "Add bounds checking".to_string(),
            },
            AuditRule {
                id: "GAS001".to_string(),
                name: "High Gas Usage".to_string(),
                description: "Function consumes excessive gas".to_string(),
                severity: Severity::Medium,
                category: RuleCategory::GasOptimization,
                pattern: Pattern::Custom(Box::new(|_| false)),
                recommendation: "Optimize gas consumption".to_string(),
            },
        ]
    }
    
    pub fn audit(&self, module: &WasmModule) -> AuditReport {
        let mut all_findings = Vec::new();
        
        // Run all analyzers
        for analyzer in &self.analyzers {
            let findings = analyzer.analyze(module);
            all_findings.extend(findings);
        }
        
        // Apply rules
        for rule in &self.rules {
            if self.rule_matches(rule, module) {
                all_findings.push(AuditFinding {
                    rule_id: rule.id.clone(),
                    severity: rule.severity.clone(),
                    location: Location {
                        offset: 0,
                        function: None,
                        line: None,
                    },
                    description: rule.description.clone(),
                    evidence: String::new(),
                    recommendation: rule.recommendation.clone(),
                });
            }
        }
        
        // Generate summary
        let summary = self.generate_summary(&all_findings);
        
        // Generate recommendations
        let recommendations = self.generate_recommendations(&all_findings);
        
        AuditReport {
            findings: all_findings,
            summary,
            recommendations,
        }
    }
    
    fn rule_matches(&self, rule: &AuditRule, module: &WasmModule) -> bool {
        match &rule.pattern {
            Pattern::OpcodePattern(opcodes) => {
                // Check if pattern exists in module
                module.code.windows(opcodes.len()).any(|window| window == opcodes.as_slice())
            }
            Pattern::ImportPattern(name) => {
                module.imports.iter().any(|i| i.name.contains(name))
            }
            Pattern::FunctionPattern(name) => {
                module.functions.iter().any(|f| f.name.contains(name))
            }
            Pattern::Custom(checker) => checker(module),
        }
    }
    
    fn generate_summary(&self, findings: &[AuditFinding]) -> AuditSummary {
        let total = findings.len();
        let critical = findings.iter().filter(|f| matches!(f.severity, Severity::Critical)).count();
        let high = findings.iter().filter(|f| matches!(f.severity, Severity::High)).count();
        let medium = findings.iter().filter(|f| matches!(f.severity, Severity::Medium)).count();
        let low = findings.iter().filter(|f| matches!(f.severity, Severity::Low)).count();
        let informational = findings.iter().filter(|f| matches!(f.severity, Severity::Informational)).count();
        
        let risk_score = (critical as f64 * 0.4 + high as f64 * 0.3 + medium as f64 * 0.2 + low as f64 * 0.1).min(1.0);
        
        AuditSummary {
            total_findings: total,
            critical,
            high,
            medium,
            low,
            informational,
            risk_score,
        }
    }
    
    fn generate_recommendations(&self, findings: &[AuditFinding]) -> Vec<String> {
        let mut recommendations = Vec::new();
        
        for finding in findings {
            if !recommendations.contains(&finding.recommendation) {
                recommendations.push(finding.recommendation.clone());
            }
        }
        
        recommendations
    }
}

pub struct ReportGenerator;

impl ReportGenerator {
    pub fn new() -> Self {
        Self
    }
    
    pub fn generate(&self, report: &AuditReport) -> String {
        let mut output = String::new();
        
        output.push_str("# Wasm Security Audit Report\n\n");
        
        output.push_str("## Summary\n\n");
        output.push_str(&format!("- Total Findings: {}\n", report.summary.total_findings));
        output.push_str(&format!("- Critical: {}\n", report.summary.critical));
        output.push_str(&format!("- High: {}\n", report.summary.high));
        output.push_str(&format!("- Medium: {}\n", report.summary.medium));
        output.push_str(&format!("- Low: {}\n", report.summary.low));
        output.push_str(&format!("- Informational: {}\n", report.summary.informational));
        output.push_str(&format!("- Risk Score: {:.2}\n\n", report.summary.risk_score));
        
        output.push_str("## Findings\n\n");
        for finding in &report.findings {
            output.push_str(&format!("### {} ({:?})\n\n", finding.rule_id, finding.severity));
            output.push_str(&format!("**Description**: {}\n\n", finding.description));
            output.push_str(&format!("**Evidence**: {}\n\n", finding.evidence));
            output.push_str(&format!("**Recommendation**: {}\n\n", finding.recommendation));
        }
        
        output.push_str("## Recommendations\n\n");
        for (i, rec) in report.recommendations.iter().enumerate() {
            output.push_str(&format!("{}. {}\n", i + 1, rec));
        }
        
        output
    }
}

pub struct WasmModule {
    pub imports: Vec<Import>,
    pub functions: Vec<FunctionDef>,
    pub code: Vec<Instruction>,
    pub memory: Option<MemoryDef>,
}

pub struct Import {
    pub module: String,
    pub name: String,
}

pub struct FunctionDef {
    pub name: String,
    pub params: Vec<ValType>,
    pub results: Vec<ValType>,
    pub code: Vec<Instruction>,
}

pub enum Instruction {
    Nop,
    Block { block_type: BlockType },
    Loop { block_type: BlockType },
    If { block_type: BlockType },
    Else,
    End,
    Br { label: u32 },
    BrIf { label: u32 },
    Return,
    Call { function_index: u32 },
    LocalGet { index: u32 },
    LocalSet { index: u32 },
    LocalTee { index: u32 },
    I32Const { value: i32 },
    I64Const { value: i64 },
    I32Add,
    I32Sub,
    I32Mul,
    I32DivS,
    I64Add,
    I64Sub,
    I64Mul,
    I64DivS,
    MemoryLoad { size: u32, offset: u32 },
    MemoryStore { size: u32, offset: u32 },
    MemoryGrow { pages: u32 },
    MemorySize,
}

pub enum BlockType {
    Empty,
    Value(ValType),
}

pub enum ValType {
    I32,
    I64,
    F32,
    F64,
}

pub struct MemoryDef {
    pub initial: u32,
    pub maximum: Option<u32>,
}
```

---

## 15.10 Complete Smart Contract Example

### Exemplo Completo de Smart Contract

```rust
// complete-smart-contract/src/lib.rs
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct SmartContract {
    state: ContractState,
    config: ContractConfig,
    gas_meter: GasMeter,
    event_log: Vec<Event>,
}

#[derive(Debug, Clone)]
pub struct ContractState {
    pub owner: [u8; 32],
    pub balances: HashMap<[u8; 32], u128>,
    pub total_supply: u128,
    pub allowances: HashMap<([u8; 32], [u8; 32]), u128>,
    pub name: String,
    pub symbol: String,
    pub decimals: u8,
    pub paused: bool,
    pub blacklisted: Vec<[u8; 32]>,
}

#[derive(Debug, Clone)]
pub struct ContractConfig {
    pub name: String,
    pub symbol: String,
    pub decimals: u8,
    pub initial_supply: u128,
    pub max_supply: Option<u128>,
    pub allow_minting: bool,
    pub allow_burning: bool,
    pub pausable: bool,
    pub blacklisted: bool,
}

#[derive(Debug, Clone)]
pub struct GasMeter {
    pub consumed: u64,
    pub limit: u64,
    pub price: u64,
}

#[derive(Debug, Clone)]
pub struct Event {
    pub name: String,
    pub data: HashMap<String, String>,
    pub timestamp: u64,
}

#[derive(Debug)]
pub enum ContractError {
    InsufficientBalance { available: u128, required: u128 },
    InsufficientAllowance { available: u128, required: u128 },
    Unauthorized,
    Paused,
    Blacklisted,
    InvalidAddress,
    InvalidAmount,
    Overflow,
    Underflow,
    MaxSupplyExceeded,
    MintingDisabled,
    BurningDisabled,
    SelfTransfer,
    ZeroAmount,
}

impl std::fmt::Display for ContractError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::InsufficientBalance { available, required } => {
                write!(f, "Insufficient balance: {} < {}", available, required)
            }
            Self::InsufficientAllowance { available, required } => {
                write!(f, "Insufficient allowance: {} < {}", available, required)
            }
            Self::Unauthorized => write!(f, "Unauthorized"),
            Self::Paused => write!(f, "Contract is paused"),
            Self::Blacklisted => write!(f, "Address is blacklisted"),
            Self::InvalidAddress => write!(f, "Invalid address"),
            Self::InvalidAmount => write!(f, "Invalid amount"),
            Self::Overflow => write!(f, "Arithmetic overflow"),
            Self::Underflow => write!(f, "Arithmetic underflow"),
            Self::MaxSupplyExceeded => write!(f, "Max supply exceeded"),
            Self::MintingDisabled => write!(f, "Minting is disabled"),
            Self::BurningDisabled => write!(f, "Burning is disabled"),
            Self::SelfTransfer => write!(f, "Cannot transfer to self"),
            Self::ZeroAmount => write!(f, "Amount cannot be zero"),
        }
    }
}

impl SmartContract {
    pub fn new(config: ContractConfig) -> Self {
        let mut state = ContractState {
            owner: [0; 32],
            balances: HashMap::new(),
            total_supply: 0,
            allowances: HashMap::new(),
            name: config.name.clone(),
            symbol: config.symbol.clone(),
            decimals: config.decimals,
            paused: false,
            blacklisted: Vec::new(),
        };
        
        // Set owner to deployer (in real implementation)
        let owner = [1; 32];
        state.owner = owner;
        
        // Mint initial supply
        state.balances.insert(owner, config.initial_supply);
        state.total_supply = config.initial_supply;
        
        Self {
            state,
            config,
            gas_meter: GasMeter {
                consumed: 0,
                limit: 30_000_000,
                price: 1,
            },
            event_log: Vec::new(),
        }
    }
    
    pub fn name(&self) -> String {
        self.state.name.clone()
    }
    
    pub fn symbol(&self) -> String {
        self.state.symbol.clone()
    }
    
    pub fn decimals(&self) -> u8 {
        self.state.decimals
    }
    
    pub fn total_supply(&self) -> u128 {
        self.state.total_supply
    }
    
    pub fn balance_of(&self, account: [u8; 32]) -> u128 {
        self.state.balances.get(&account).copied().unwrap_or(0)
    }
    
    pub fn allowance(&self, owner: [u8; 32], spender: [u8; 32]) -> u128 {
        self.state.allowances.get(&(owner, spender)).copied().unwrap_or(0)
    }
    
    pub fn transfer(
        &mut self,
        from: [u8; 32],
        to: [u8; 32],
        amount: u128,
    ) -> Result<(), ContractError> {
        // Pre-conditions
        self.pre_transfer_check()?;
        
        if amount == 0 {
            return Err(ContractError::ZeroAmount);
        }
        
        if from == to {
            return Err(ContractError::SelfTransfer);
        }
        
        if self.state.blacklisted.contains(&from) || self.state.blacklisted.contains(&to) {
            return Err(ContractError::Blacklisted);
        }
        
        let from_balance = self.balance_of(from);
        if from_balance < amount {
            return Err(ContractError::InsufficientBalance {
                available: from_balance,
                required: amount,
            });
        }
        
        // Effects
        self.state.balances.insert(from, from_balance - amount);
        
        let to_balance = self.balance_of(to);
        self.state
            .balances
            .insert(to, to_balance.checked_add(amount).ok_or(ContractError::Overflow)?);
        
        // Events
        self.emit_event("Transfer", HashMap::from([
            ("from".to_string(), format!("0x{}", hex::encode(from))),
            ("to".to_string(), format!("0x{}", hex::encode(to))),
            ("value".to_string(), amount.to_string()),
        ]));
        
        Ok(())
    }
    
    pub fn approve(
        &mut self,
        owner: [u8; 32],
        spender: [u8; 32],
        amount: u128,
    ) -> Result<(), ContractError> {
        self.pre_transfer_check()?;
        
        if self.state.blacklisted.contains(&owner) || self.state.blacklisted.contains(&spender) {
            return Err(ContractError::Blacklisted);
        }
        
        self.state.allowances.insert((owner, spender), amount);
        
        self.emit_event("Approval", HashMap::from([
            ("owner".to_string(), format!("0x{}", hex::encode(owner))),
            ("spender".to_string(), format!("0x{}", hex::encode(spender)),
            ("value".to_string(), amount.to_string()),
        ]));
        
        Ok(())
    }
    
    pub fn transfer_from(
        &mut self,
        spender: [u8; 32],
        from: [u8; 32],
        to: [u8; 32],
        amount: u128,
    ) -> Result<(), ContractError> {
        self.pre_transfer_check()?;
        
        if amount == 0 {
            return Err(ContractError::ZeroAmount);
        }
        
        if self.state.blacklisted.contains(&from)
            || self.state.blacklisted.contains(&to)
            || self.state.blacklisted.contains(&spender)
        {
            return Err(ContractError::Blacklisted);
        }
        
        let allowance = self.allowance(from, spender);
        if allowance < amount {
            return Err(ContractError::InsufficientAllowance {
                available: allowance,
                required: amount,
            });
        }
        
        let from_balance = self.balance_of(from);
        if from_balance < amount {
            return Err(ContractError::InsufficientBalance {
                available: from_balance,
                required: amount,
            });
        }
        
        // Effects
        self.state.allowances.insert((from, spender), allowance - amount);
        self.state.balances.insert(from, from_balance - amount);
        
        let to_balance = self.balance_of(to);
        self.state
            .balances
            .insert(to, to_balance.checked_add(amount).ok_or(ContractError::Overflow)?);
        
        // Events
        self.emit_event("Transfer", HashMap::from([
            ("from".to_string(), format!("0x{}", hex::encode(from))),
            ("to".to_string(), format!("0x{}", hex::encode(to))),
            ("value".to_string(), amount.to_string()),
            ("sender".to_string(), format!("0x{}", hex::encode(spender))),
        ]));
        
        Ok(())
    }
    
    pub fn mint(
        &mut self,
        caller: [u8; 32],
        to: [u8; 32],
        amount: u128,
    ) -> Result<(), ContractError> {
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        if !self.config.allow_minting {
            return Err(ContractError::MintingDisabled);
        }
        
        if self.state.blacklisted.contains(&to) {
            return Err(ContractError::Blacklisted);
        }
        
        if let Some(max_supply) = self.config.max_supply {
            if self.state.total_supply + amount > max_supply {
                return Err(ContractError::MaxSupplyExceeded);
            }
        }
        
        // Effects
        self.state.total_supply = self
            .state
            .total_supply
            .checked_add(amount)
            .ok_or(ContractError::Overflow)?;
        
        let to_balance = self.balance_of(to);
        self.state
            .balances
            .insert(to, to_balance.checked_add(amount).ok_or(ContractError::Overflow)?);
        
        // Events
        self.emit_event("Mint", HashMap::from([
            ("to".to_string(), format!("0x{}", hex::encode(to))),
            ("value".to_string(), amount.to_string()),
        ]));
        
        Ok(())
    }
    
    pub fn burn(
        &mut self,
        caller: [u8; 32],
        amount: u128,
    ) -> Result<(), ContractError> {
        if !self.config.allow_burning {
            return Err(ContractError::BurningDisabled);
        }
        
        if self.state.blacklisted.contains(&caller) {
            return Err(ContractError::Blacklisted);
        }
        
        let balance = self.balance_of(caller);
        if balance < amount {
            return Err(ContractError::InsufficientBalance {
                available: balance,
                required: amount,
            });
        }
        
        // Effects
        self.state.total_supply = self
            .state
            .total_supply
            .checked_sub(amount)
            .ok_or(ContractError::Underflow)?;
        
        self.state.balances.insert(caller, balance - amount);
        
        // Events
        self.emit_event("Burn", HashMap::from([
            ("from".to_string(), format!("0x{}", hex::encode(caller))),
            ("value".to_string(), amount.to_string()),
        ]));
        
        Ok(())
    }
    
    pub fn pause(&mut self, caller: [u8; 32]) -> Result<(), ContractError> {
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        if !self.config.pausable {
            return Err(ContractError::Unauthorized);
        }
        
        self.state.paused = true;
        
        self.emit_event("Paused", HashMap::from([
            ("account".to_string(), format!("0x{}", hex::encode(caller))),
        ]));
        
        Ok(())
    }
    
    pub fn unpause(&mut self, caller: [u8; 32]) -> Result<(), ContractError> {
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        if !self.config.pausable {
            return Err(ContractError::Unauthorized);
        }
        
        self.state.paused = false;
        
        self.emit_event("Unpaused", HashMap::from([
            ("account".to_string(), format!("0x{}", hex::encode(caller))),
        ]));
        
        Ok(())
    }
    
    pub fn blacklist(
        &mut self,
        caller: [u8; 32],
        account: [u8; 32],
    ) -> Result<(), ContractError> {
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        if !self.config.blacklisted {
            return Err(ContractError::Unauthorized);
        }
        
        if !self.state.blacklisted.contains(&account) {
            self.state.blacklisted.push(account);
        }
        
        self.emit_event("Blacklisted", HashMap::from([
            ("account".to_string(), format!("0x{}", hex::encode(account))),
        ]));
        
        Ok(())
    }
    
    pub fn unblacklist(
        &mut self,
        caller: [u8; 32],
        account: [u8; 32],
    ) -> Result<(), ContractError> {
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        if !self.config.blacklisted {
            return Err(ContractError::Unauthorized);
        }
        
        self.state.blacklisted.retain(|&a| a != account);
        
        self.emit_event("Unblacklisted", HashMap::from([
            ("account".to_string(), format!("0x{}", hex::encode(account))),
        ]));
        
        Ok(())
    }
    
    pub fn transfer_ownership(
        &mut self,
        caller: [u8; 32],
        new_owner: [u8; 32],
    ) -> Result<(), ContractError> {
        if caller != self.state.owner {
            return Err(ContractError::Unauthorized);
        }
        
        let old_owner = self.state.owner;
        self.state.owner = new_owner;
        
        self.emit_event("OwnershipTransferred", HashMap::from([
            ("previousOwner".to_string(), format!("0x{}", hex::encode(old_owner))),
            ("newOwner".to_string(), format!("0x{}", hex::encode(new_owner))),
        ]));
        
        Ok(())
    }
    
    fn pre_transfer_check(&self) -> Result<(), ContractError> {
        if self.state.paused {
            return Err(ContractError::Paused);
        }
        Ok(())
    }
    
    fn emit_event(&mut self, name: &str, data: HashMap<String, String>) {
        self.event_log.push(Event {
            name: name.to_string(),
            data,
            timestamp: self.get_timestamp(),
        });
    }
    
    fn get_timestamp(&self) -> u64 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn create_contract() -> SmartContract {
        let config = ContractConfig {
            name: "Test Token".to_string(),
            symbol: "TST".to_string(),
            decimals: 18,
            initial_supply: 1_000_000_000_000_000_000_000_000, // 1M tokens with 18 decimals
            max_supply: Some(10_000_000_000_000_000_000_000_000), // 10M max
            allow_minting: true,
            allow_burning: true,
            pausable: true,
            blacklisted: true,
        };
        
        SmartContract::new(config)
    }
    
    #[test]
    fn test_initial_state() {
        let contract = create_contract();
        
        assert_eq!(contract.name(), "Test Token");
        assert_eq!(contract.symbol(), "TST");
        assert_eq!(contract.decimals(), 18);
        assert_eq!(contract.total_supply(), 1_000_000_000_000_000_000_000_000);
    }
    
    #[test]
    fn test_transfer() {
        let mut contract = create_contract();
        let owner = [1; 32];
        let recipient = [2; 32];
        
        let result = contract.transfer(owner, recipient, 1000);
        assert!(result.is_ok());
        
        assert_eq!(contract.balance_of(recipient), 1000);
    }
    
    #[test]
    fn test_insufficient_balance() {
        let mut contract = create_contract();
        let sender = [2; 32]; // No balance
        let recipient = [3; 32];
        
        let result = contract.transfer(sender, recipient, 1000);
        assert!(matches!(result, Err(ContractError::InsufficientBalance { .. })));
    }
    
    #[test]
    fn test_mint() {
        let mut contract = create_contract();
        let owner = [1; 32];
        let recipient = [2; 32];
        
        let result = contract.mint(owner, recipient, 500);
        assert!(result.is_ok());
        
        assert_eq!(contract.balance_of(recipient), 500);
        assert_eq!(
            contract.total_supply(),
            1_000_000_000_000_000_000_000_000 + 500
        );
    }
    
    #[test]
    fn test_unauthorized_mint() {
        let mut contract = create_contract();
        let unauthorized = [2; 32];
        let recipient = [3; 32];
        
        let result = contract.mint(unauthorized, recipient, 500);
        assert!(matches!(result, Err(ContractError::Unauthorized)));
    }
    
    #[test]
    fn test_burn() {
        let mut contract = create_contract();
        let owner = [1; 32];
        
        let initial_balance = contract.balance_of(owner);
        let burn_amount = 1000;
        
        let result = contract.burn(owner, burn_amount);
        assert!(result.is_ok());
        
        assert_eq!(contract.balance_of(owner), initial_balance - burn_amount);
        assert_eq!(
            contract.total_supply(),
            1_000_000_000_000_000_000_000_000 - burn_amount
        );
    }
    
    #[test]
    fn test_pause() {
        let mut contract = create_contract();
        let owner = [1; 32];
        
        let result = contract.pause(owner);
        assert!(result.is_ok());
        assert!(contract.state.paused);
        
        // Try to transfer while paused
        let recipient = [2; 32];
        let result = contract.transfer(owner, recipient, 1000);
        assert!(matches!(result, Err(ContractError::Paused)));
    }
    
    #[test]
    fn test_blacklist() {
        let mut contract = create_contract();
        let owner = [1; 32];
        let account = [2; 32];
        
        let result = contract.blacklist(owner, account);
        assert!(result.is_ok());
        
        assert!(contract.state.blacklisted.contains(&account));
        
        // Try to transfer from blacklisted account
        let recipient = [3; 32];
        let result = contract.transfer(account, recipient, 1000);
        assert!(matches!(result, Err(ContractError::Blacklisted)));
    }
    
    #[test]
    fn test_transfer_ownership() {
        let mut contract = create_contract();
        let owner = [1; 32];
        let new_owner = [2; 32];
        
        let result = contract.transfer_ownership(owner, new_owner);
        assert!(result.is_ok());
        
        assert_eq!(contract.state.owner, new_owner);
    }
}
```

---

## Conclusão

Neste capítulo, exploramos como o WebAssembly está sendo utilizado em blockchain para smart contracts. Cobrimos desde plataformas como Polkadot ink!, NEAR SDK e Cosmos CosmWasm até o futuro do Ethereum com eWASM.

Os pontos-chave abordados incluem:

1. **Smart Contracts in Wasm**: Fundamentos e estrutura básica
2. **Polkadot ink!**: Framework Rust para Polkadot
3. **NEAR SDK**: Smart contracts para NEAR Protocol
4. **Cosmos CosmWasm**: Contratos interoperáveis no Cosmos
5. **Ethereum eWASM**: Futuro do Ethereum com WASM
6. **Security Model Comparison**: Comparação detalhada de modelos
7. **Gas Metering**: Medição de recursos eficiente
8. **Deterministic Execution**: Garantia de execução determinística
9. **Audit Tools**: Ferramentas de auditoria e análise
10. **Complete Example**: Smart contract completo com múltiplos recursos

O WebAssembly oferece vantagens significativas sobre a EVM tradicional, incluindo melhor desempenho, segurança mais robusta e suporte a múltiplas linguagens de programação. No entanto, a adoção ainda está em estágios iniciais, e cada plataforma blockchain tem suas próprias considerações e trade-offs.

À medida que o ecossistema WASM para blockchain amadurece, esperamos ver mais padronização, ferramentas melhores e maior adoção por parte de desenvolvedores e empresas.

---

## Referências

1. Polkadot ink! Documentation - https://ink.substrate.io/
2. NEAR SDK Documentation - https://docs.near.org/sdk/rust/introduction
3. CosmWasm Documentation - https://docs.cosmwasm.com/
4. Ethereum eWASM - https://github.com/ewasm
5. WebAssembly Specification - https://webassembly.org/spec/
6. Wasmtime Documentation - https://docs.wasmtime.dev/
---

*[Capítulo anterior: 14 — Edge Computing](14-edge-computing.md)*
*[Próximo capítulo: 16 — Compliance](16-compliance.md)*
