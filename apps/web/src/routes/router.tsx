import { createBrowserRouter } from "react-router";

import { Layout } from "../components/Layout";
import { SearchPage } from "../features/search/SearchPage";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [{ index: true, element: <SearchPage /> }],
  },
]);
