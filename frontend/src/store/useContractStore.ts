import { create } from "zustand";

export interface Contract {
  id: number;
  filename: string;
  upload_path: string;
  status: "pending" | "ingested" | "analyzed" | "failed";
  created_at: string;
  file_size?: number;
  document_type?: string;
}

interface ContractState {
  contracts: Contract[];
  activeContractId: number | null;
  searchQuery: string;
  filterStatus: string;
  isLoading: boolean;
  setContracts: (contracts: Contract[]) => void;
  setActiveContractId: (id: number | null) => void;
  setSearchQuery: (query: string) => void;
  setFilterStatus: (status: string) => void;
  setIsLoading: (loading: boolean) => void;
  removeContract: (id: number) => void;
  clearStore: () => void;
}

export const useContractStore = create<ContractState>((set) => ({
  contracts: [],
  activeContractId: null,
  searchQuery: "",
  filterStatus: "all",
  isLoading: false,

  setContracts: (contracts) => set({ contracts }),
  setActiveContractId: (activeContractId) => set({ activeContractId }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setFilterStatus: (filterStatus) => set({ filterStatus }),
  setIsLoading: (isLoading) => set({ isLoading }),
  removeContract: (id) =>
    set((state) => ({
      contracts: state.contracts.filter((c) => c.id !== id),
      activeContractId: state.activeContractId === id ? null : state.activeContractId,
    })),
  clearStore: () =>
    set({
      contracts: [],
      activeContractId: null,
      searchQuery: "",
      filterStatus: "all",
      isLoading: false,
    }),
}));
